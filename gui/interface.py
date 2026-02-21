import json
import logging
import queue
import threading

import customtkinter as ctk

from core.config import CONFIG_PATH

logger = logging.getLogger(__name__)
MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
MAX_LOG_LINES = 500


class QueueLogHandler(logging.Handler):
    """Logging handler that puts formatted records into a queue for the GUI."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            self.log_queue.put(self.format(record))
        except Exception:
            self.handleError(record)


class LogWindow(ctk.CTkToplevel):
    """Floating log viewer — always on top, hides on close instead of destroying."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Log — Auto-StopotS")
        self.geometry("520x360")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        ctk.CTkLabel(self, text="Log", font=("", 13, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        self._textbox = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def append(self, msg: str) -> None:
        self._textbox.configure(state="normal")
        self._textbox.insert("end", msg + "\n")
        line_count = int(self._textbox.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            self._textbox.delete("1.0", f"{line_count - MAX_LOG_LINES + 1}.0")
        self._textbox.configure(state="disabled")
        self._textbox.see("end")

    def show(self) -> None:
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)


class ControlPanel(ctk.CTkToplevel):
    """Small floating control panel shown after the bot starts — always on top."""

    def __init__(self, master, enabled_event: threading.Event, on_close):
        super().__init__(master)
        self.title("Auto-StopotS")
        self.geometry("250x130")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", on_close)

        self._enabled_event = enabled_event
        self._log_window: LogWindow | None = None

        self._build_ui()

    def _build_ui(self):
        self._status_label = ctk.CTkLabel(self, text="● Status: Ativo", anchor="w")
        self._status_label.pack(fill="x", padx=14, pady=(14, 8))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))

        self._toggle_var = ctk.StringVar(value="on")
        self._toggle_switch = ctk.CTkSwitch(
            row,
            text="Ativar",
            variable=self._toggle_var,
            onvalue="on",
            offvalue="off",
            command=self._on_toggle,
        )
        self._toggle_switch.select()
        self._toggle_switch.pack(side="left")

        ctk.CTkButton(row, text="Log", width=55, command=self._on_log_click).pack(
            side="right"
        )

    def _on_toggle(self):
        if self._toggle_var.get() == "on":
            self._enabled_event.set()
            self._status_label.configure(text="● Status: Ativo")
        else:
            self._enabled_event.clear()
            self._status_label.configure(text="● Status: Parado")

    def _on_log_click(self):
        if self._log_window is None or not self._log_window.winfo_exists():
            self._log_window = LogWindow(self)
        else:
            self._log_window.show()

    def append_log(self, msg: str) -> None:
        if self._log_window and self._log_window.winfo_exists():
            self._log_window.append(msg)

    def deactivate(self) -> None:
        """Force switch off — called on the main thread after a fatal API key error."""
        self._enabled_event.clear()
        self._toggle_var.set("off")
        self._toggle_switch.deselect()
        self._status_label.configure(text="● Status: Parado (erro de API Key)")


class StopotSApp(ctk.CTk):
    """
    Entry-point window.

    Shows the config form first. On start it hides itself and spawns
    a floating ControlPanel that stays above the Playwright browser.
    """

    def __init__(self):
        super().__init__()
        self.title("Auto-StopotS — Configuração")
        self.geometry("420x255")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._enabled_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._bot_thread: threading.Thread | None = None
        self._control_panel: ControlPanel | None = None

        self._setup_logging()
        self._config = self._load_config()
        self._build_config_ui()
        self._poll_log_queue()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Logging ────────────────────────────────────────────────────

    def _setup_logging(self):
        handler = QueueLogHandler(self._log_queue)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
        )
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)

    # ── Config persistence ──────────────────────────────────────────

    @staticmethod
    def _load_config() -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self) -> None:
        config = {
            "openai_api_key": self._api_key_entry.get().strip(),
            "model": self._model_var.get(),
        }
        CONFIG_PATH.write_text(json.dumps(config, indent=4), encoding="utf-8")

    # ── Config UI ──────────────────────────────────────────────────

    def _build_config_ui(self):
        ctk.CTkLabel(self, text="Configurações", font=("", 14, "bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )

        row_key = ctk.CTkFrame(self, fg_color="transparent")
        row_key.pack(fill="x", padx=16, pady=3)
        ctk.CTkLabel(row_key, text="API Key:", width=68, anchor="w").pack(side="left")
        self._api_key_entry = ctk.CTkEntry(row_key, show="*", width=290)
        self._api_key_entry.pack(side="left", padx=(6, 0))
        if self._config.get("openai_api_key"):
            self._api_key_entry.insert(0, self._config["openai_api_key"])
        self._api_key_entry.bind("<KeyRelease>", lambda _e: self._refresh_start_btn())

        row_model = ctk.CTkFrame(self, fg_color="transparent")
        row_model.pack(fill="x", padx=16, pady=3)
        ctk.CTkLabel(row_model, text="Modelo:", width=68, anchor="w").pack(side="left")
        self._model_var = ctk.StringVar(value=self._config.get("model", MODEL_OPTIONS[0]))
        ctk.CTkOptionMenu(
            row_model, variable=self._model_var, values=MODEL_OPTIONS, width=200
        ).pack(side="left", padx=(6, 0))

        self._start_btn = ctk.CTkButton(
            self, text="Iniciar", command=self._on_start, width=160
        )
        self._start_btn.pack(pady=(16, 4))

        self._status_label = ctk.CTkLabel(self, text="", text_color="#FF6B6B")
        self._status_label.pack(pady=(0, 8))

        self._refresh_start_btn()

    def _refresh_start_btn(self):
        has_key = bool(self._api_key_entry.get().strip())
        self._start_btn.configure(state="normal" if has_key else "disabled")

    # ── Start ──────────────────────────────────────────────────────

    def _on_start(self):
        self._save_config()
        self._start_btn.configure(state="disabled", text="Verificando navegador...")
        threading.Thread(target=self._ensure_browser_then_start, daemon=True).start()

    def _ensure_browser_then_start(self):
        try:
            if not self._is_chromium_installed():
                self.after(0, lambda: self._start_btn.configure(
                    text="Baixando Chromium... (aguarde)"
                ))
            self._install_browser()
        except Exception as e:
            msg = str(e)
            logger.error(f"Falha ao preparar navegador: {msg}")
            self.after(0, lambda m=msg: self._on_browser_error(m))
            return
        self.after(0, self._launch_bot)

    def _on_browser_error(self, msg: str):
        self._start_btn.configure(state="normal", text="Iniciar")
        self._status_label.configure(text=f"Erro: {msg[:60]}")

    @staticmethod
    def _is_chromium_installed() -> bool:
        import glob
        import os
        from pathlib import Path
        patterns = [
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-*" / "chrome-win" / "chrome.exe"),
            str(Path.home() / ".cache" / "ms-playwright" / "chromium-*" / "chrome-linux" / "chrome"),
        ]
        return any(glob.glob(p) for p in patterns)

    @staticmethod
    def _install_browser():
        import subprocess
        import sys

        is_frozen = getattr(sys, "frozen", False)

        if is_frozen:
            from playwright._impl._driver import compute_driver_executable
            driver = str(compute_driver_executable())

        if sys.platform == "win32":
            # shell=True + quoted string handles .cmd drivers, UNC paths and spaces.
            shell_cmd = (
                f'"{driver}" install chromium'
                if is_frozen
                else f'"{sys.executable}" -m playwright install chromium'
            )
            proc = subprocess.run(
                shell_cmd, shell=True, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
        else:
            cmd = (
                [driver, "install", "chromium"]
                if is_frozen
                else [sys.executable, "-m", "playwright", "install", "chromium"]
            )
            proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or "Erro ao instalar Chromium")

    def _launch_bot(self):
        self._enabled_event.set()
        x, y = self.winfo_x(), self.winfo_y()
        self._control_panel = ControlPanel(
            master=self,
            enabled_event=self._enabled_event,
            on_close=self._on_close,
        )
        self._control_panel.geometry(f"250x130+{x}+{y}")

        from main import run_bot_thread
        self._bot_thread = threading.Thread(
            target=run_bot_thread,
            args=(self._enabled_event, self._shutdown_event, self._deactivate_bot),
            daemon=True,
        )
        self._bot_thread.start()
        self.withdraw()

    # ── Callbacks ──────────────────────────────────────────────────

    def _deactivate_bot(self):
        def _apply():
            if self._control_panel and self._control_panel.winfo_exists():
                self._control_panel.deactivate()
        self.after(0, _apply)

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
            if self._control_panel and self._control_panel.winfo_exists():
                self._control_panel.append_log(msg)
        self.after(100, self._poll_log_queue)
