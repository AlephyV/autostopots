import asyncio
import logging
import random
from collections.abc import Callable

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def wait_for_round(page: Page) -> None:
    """Wait until a new round is active (inputs visible and editable)."""
    await page.wait_for_selector("#inputText-0", state="visible", timeout=60000)
    locator = page.locator("#inputText-0")
    for _ in range(30):
        if await locator.is_editable():
            return
        await asyncio.sleep(1)
    raise TimeoutError("Round inputs never became editable")


async def get_round_letter(page: Page) -> str:
    """
    Read the current round letter.
    Selector: div.maskLetter p  (e.g. <p class="... animate">D</p>)
    """
    locator = page.locator("div.maskLetter p")
    letter = (await locator.text_content()).strip()
    if not letter or len(letter) != 1:
        raise RuntimeError(f"Invalid round letter: '{letter}'")
    return letter


async def get_categories(page: Page) -> list[dict]:
    """
    Read visible categories for the current round.
    Returns: [{"name": "Fruta", "full_name": "Fruta", "input_id": "inputText-0"}, ...]
    """
    categories = await page.evaluate("""
        () => {
            const result = [];
            let i = 0;
            while (true) {
                const input = document.querySelector(`#inputText-${i}`);
                if (!input) break;

                const label = input.closest('label');

                let name = `Category ${i + 1}`;
                const legendP = label ? label.querySelector('legend p') : null;
                if (legendP) {
                    name = legendP.textContent.trim();
                }

                let fullName = name;
                const tooltipP = label ? label.querySelector('.tooltip p') : null;
                if (tooltipP) {
                    fullName = tooltipP.textContent.trim();
                }

                result.push({
                    name: name,
                    full_name: fullName,
                    input_id: `inputText-${i}`
                });
                i++;
            }
            return result;
        }
    """)
    return categories


async def is_round_active(page: Page) -> bool:
    """Check if the round is still active (first input exists and is editable)."""
    try:
        locator = page.locator("#inputText-0")
        if await locator.count() == 0:
            return False
        editable = await locator.is_editable()
        logger.debug(f"is_editable: {editable}")
        return editable
    except Exception:
        return False


async def fill_input(page: Page, input_id: str, text: str) -> None:
    """
    Fill a single input simulating human typing with random delays.
    Raises RuntimeError if the round ends before or during typing.
    """
    if not await is_round_active(page):
        raise RuntimeError("Round encerrado — preenchimento interrompido.")

    locator = page.locator(f"#{input_id}")

    if await locator.count() == 0:
        logger.warning(f"#{input_id} nao encontrado, indo para o proximo")
        return

    await locator.click(force=True)
    await page.keyboard.press("Control+A")
    await asyncio.sleep(random.uniform(0.15, 0.4))
    for char in text:
        if not await is_round_active(page):
            raise RuntimeError("Round encerrado — preenchimento interrompido.")
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.02, 0.06))


async def fill_all_categories(
    page: Page,
    answers: dict[str, str],
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """
    Fill all category inputs with the given answers.
    answers: {"inputText-0": "Word1", "inputText-1": "Word2", ...}

    Stops early if should_stop() returns True or if the round ends mid-typing.
    """
    try:
        for input_id, text in answers.items():
            if should_stop and should_stop():
                logger.info("Bot desativado — preenchimento interrompido.")
                return
            try:
                await fill_input(page, input_id, text)
                await asyncio.sleep(random.uniform(0.3, 0.7))
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"Falha ao preencher {input_id}: {e}")
    except RuntimeError:
        logger.error("Round encerrado, preenchimento interrompido")


STOPOTS_URL = "https://stopots.com/pt/"
