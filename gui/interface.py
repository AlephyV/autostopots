import json
import logging
import queue
import threading
from pathlib import Path

import customtkinter as ctk

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
MAX_LOG_LINES = 500


class QueueLogHandler(logging.Handler):
    """Logging handler that puts formatted records into a queue for the GUI."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


class StopotSApp(ctk.CTk):
    """Main GUI window for the Auto-StopotS bot."""

    def __init__(self):
        super().__init__()

        self.title("Auto-StopotS")
        self.geometry("520x560")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Threading primitives
        self._enabled_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._bot_thread: threading.Thread | None = None

        # Setup logging
        self._setup_logging()

        # Load existing config
        self._config = self._load_config()

        # Build UI
        self._build_config_frame()
        self._build_control_frame()
        self._build_log_frame()

        # Start polling log queue
        self._poll_log_queue()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Logging setup ──────────────────────────────────────────────

    def _setup_logging(self):
        handler = QueueLogHandler(self._log_queue)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(message)s", datefmt="%H:%M:%S"
        ))
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

    # ── Config ─────────────────────────────────────────────────────

    @staticmethod
    def _load_config() -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self):
        api_key = self._api_key_entry.get().strip()
        model = self._model_var.get()
        config = {"openai_api_key": api_key, "model": model}
        CONFIG_PATH.write_text(json.dumps(config, indent=4), encoding="utf-8")
        logger.info("Configurações salvas.")

    # ── UI builders ────────────────────────────────────────────────

    def _build_config_frame(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(frame, text="Configurações", font=("", 14, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        # API Key
        row_key = ctk.CTkFrame(frame, fg_color="transparent")
        row_key.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_key, text="API Key:").pack(side="left")
        self._api_key_entry = ctk.CTkEntry(row_key, show="*", width=340)
        self._api_key_entry.pack(side="left", padx=(8, 0))

        # Model
        row_model = ctk.CTkFrame(frame, fg_color="transparent")
        row_model.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_model, text="Modelo:").pack(side="left")
        self._model_var = ctk.StringVar(
            value=self._config.get("model", MODEL_OPTIONS[0])
        )
        ctk.CTkOptionMenu(
            row_model, variable=self._model_var, values=MODEL_OPTIONS, width=200
        ).pack(side="left", padx=(8, 0))

        # Save button
        ctk.CTkButton(frame, text="Salvar Configurações", command=self._save_config).pack(
            padx=10, pady=(6, 10)
        )

    def _build_control_frame(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame, text="Controle", font=("", 14, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 4))

        self._start_btn = ctk.CTkButton(row, text="Começar", command=self._on_start_click)
        self._start_btn.pack(side="left")

        self._toggle_var = ctk.StringVar(value="off")
        self._toggle_switch = ctk.CTkSwitch(
            row,
            text="Ativar",
            variable=self._toggle_var,
            onvalue="on",
            offvalue="off",
            command=self._on_toggle_change,
        )
        self._toggle_switch.pack(side="left", padx=(20, 0))
        self._toggle_switch.configure(state="disabled")

        self._status_label = ctk.CTkLabel(frame, text="Status: Parado")
        self._status_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_log_frame(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        ctk.CTkLabel(frame, text="Log", font=("", 14, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        self._log_textbox = ctk.CTkTextbox(frame, state="disabled", wrap="word")
        self._log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ── Actions ────────────────────────────────────────────────────

    def _on_start_click(self):
        self._save_config()

        self._start_btn.configure(state="disabled", text="Navegador aberto")
        self._toggle_switch.configure(state="normal")

        # Start with bot enabled
        self._toggle_var.set("on")
        self._toggle_switch.select()
        self._enabled_event.set()
        self._status_label.configure(text="Status: Ativo")

        from main import run_bot_thread

        self._bot_thread = threading.Thread(
            target=run_bot_thread,
            args=(self._enabled_event, self._shutdown_event, self._deactivate_bot),
            daemon=True,
        )
        self._bot_thread.start()

    def _deactivate_bot(self):
        """Called from the bot thread on a fatal API key error — updates the GUI."""
        self.after(0, self._apply_deactivated_state)

    def _apply_deactivated_state(self):
        self._enabled_event.clear()
        self._toggle_var.set("off")
        self._toggle_switch.deselect()
        self._status_label.configure(text="Status: Parado (erro de API Key)")

    def _on_toggle_change(self):
        if self._toggle_var.get() == "on":
            self._enabled_event.set()
            self._status_label.configure(text="Status: Ativo")
        else:
            self._enabled_event.clear()
            self._status_label.configure(text="Status: Parado")

    def _on_close(self):
        self._shutdown_event.set()
        if self._bot_thread and self._bot_thread.is_alive():
            self._bot_thread.join(timeout=3)
        self.destroy()

    # ── Log polling ────────────────────────────────────────────────

    def _poll_log_queue(self):
        while True:
            try:
                msg = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._log_textbox.configure(state="normal")
            self._log_textbox.insert("end", msg + "\n")
            self._log_textbox.configure(state="disabled")
            self._log_textbox.see("end")

        # Trim excess lines
        self._trim_log()

        self.after(100, self._poll_log_queue)

    def _trim_log(self):
        self._log_textbox.configure(state="normal")
        line_count = int(self._log_textbox.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            excess = line_count - MAX_LOG_LINES
            self._log_textbox.delete("1.0", f"{excess + 1}.0")
        self._log_textbox.configure(state="disabled")
