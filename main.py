import asyncio
import logging
import threading

from playwright.async_api import async_playwright

from core.manipulator import (
    wait_for_round,
    get_round_letter,
    get_categories,
    fill_all_categories,
    is_round_active,
    STOPOTS_URL,
)
from core.intelligence import generate_answers, InvalidAPIKeyError
from core.config import get_chromium_executable

logger = logging.getLogger(__name__)


class BotController:
    """Orchestrates the bot loop in a background thread with asyncio."""

    def __init__(
        self,
        enabled_event: threading.Event,
        shutdown_event: threading.Event,
        on_disable_callback=None,
    ):
        self.enabled_event = enabled_event
        self.shutdown_event = shutdown_event
        self._on_disable_callback = on_disable_callback
        self._playwright = None
        self._browser = None
        self._page = None

    async def bot_loop(self):
        """Main bot loop: open browser, then wait for rounds and play."""
        self._playwright = await async_playwright().start()
        launch_kwargs = {"headless": False}
        if chromium_exe := get_chromium_executable():
            launch_kwargs["executable_path"] = chromium_exe
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        context = await self._browser.new_context()
        self._page = await context.new_page()

        await self._page.goto(STOPOTS_URL)
        logger.info("Navegador aberto no StopotS.")
        logger.info("Entre numa sala e inicie a partida.")

        try:
            while not self.shutdown_event.is_set():
                if not self.enabled_event.is_set():
                    await asyncio.sleep(0.5)
                    continue

                logger.info("Aguardando rodada começar...")
                try:
                    await wait_for_round(self._page)
                except Exception:
                    if self.shutdown_event.is_set():
                        break
                    logger.info("Timeout aguardando rodada — tentando novamente...")
                    continue

                if not self.enabled_event.is_set() or self.shutdown_event.is_set():
                    continue

                try:
                    await self._play_round()
                except Exception as e:
                    logger.error(f"Erro durante a rodada: {e}")

                # Wait for current round to end, but break if disabled
                while (
                    not self.shutdown_event.is_set()
                    and self.enabled_event.is_set()
                    and await is_round_active(self._page)
                ):
                    await asyncio.sleep(1)
        finally:
            await self.shutdown()

    async def _play_round(self):
        """Read round data, generate answers with AI, and fill inputs."""
        letter = await get_round_letter(self._page)
        logger.info(f"Letra da rodada: {letter}")

        categories = await get_categories(self._page)
        logger.info(f"{len(categories)} categorias encontradas:")
        for cat in categories:
            display = cat["name"]
            if cat["full_name"] != cat["name"]:
                display += f" ({cat['full_name']})"
            logger.info(f"    - {display} -> #{cat['input_id']}")

        if not self.enabled_event.is_set():
            logger.info("Bot desativado — pulando rodada.")
            return

        logger.info("Consultando IA...")
        try:
            answers = await generate_answers(letter, categories)
        except InvalidAPIKeyError:
            self.enabled_event.clear()
            logger.error(
                "Bot desativado! Troque/corrija a API Key, salve e ative novamente."
            )
            if self._on_disable_callback:
                self._on_disable_callback()
            return

        if not answers:
            logger.error("IA não retornou respostas — rodada pulada.")
            return

        id_to_name = {cat["input_id"]: cat["full_name"] for cat in categories}
        logger.info(f"Respostas geradas ({len(answers)}/{len(categories)}):")
        for input_id, answer in answers.items():
            name = id_to_name.get(input_id, input_id)
            logger.info(f"    - {name}: {answer}")

        if not self.enabled_event.is_set():
            logger.info("Bot desativado — pulando preenchimento.")
            return

        logger.info("Preenchendo categorias...")
        await fill_all_categories(
            self._page, answers,
            should_stop=lambda: not self.enabled_event.is_set(),
        )

        logger.info("Preenchimento concluído!")

    async def shutdown(self):
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


def run_bot_thread(
    enabled_event: threading.Event,
    shutdown_event: threading.Event,
    on_disable_callback=None,
):
    """Entry point for the bot daemon thread — runs its own asyncio loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    controller = BotController(enabled_event, shutdown_event, on_disable_callback)
    try:
        loop.run_until_complete(controller.bot_loop())
    except Exception as e:
        logger.error(f"Bot thread encerrada com erro: {e}")
    finally:
        loop.close()


if __name__ == "__main__":
    from gui.interface import StopotSApp

    app = StopotSApp()
    app.mainloop()
