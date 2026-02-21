import json
import logging
from pathlib import Path

from openai import AsyncOpenAI, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class InvalidAPIKeyError(Exception):
    """Raised when the API key is invalid or unauthorized."""

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict:
    """Load settings from config.json at project root."""
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Falha ao ler config.json: {e} — usando valores padrão")
        return {}


SYSTEM_PROMPT = (
    "You are a StopotS (Brazilian stop/scattergories game) expert. "
    "Given a letter and a list of categories, respond with a valid word or name "
    "for each category.\n"
    "Rules:\n"
    "- ALL answers MUST be in Brazilian Portuguese (pt-BR). "
    "Think and reason in Portuguese — never think in English and translate.\n"
    "- Every answer MUST start with the given letter (checked in pt-BR)\n"
    "- Do NOT include leading articles (O, A, Os, As, Um, Uma) — write the main word directly. "
    "WRONG: 'O Lobo de Wall Street'. CORRECT: 'Lobo de Wall Street'\n"
    "- Max 20 characters per answer\n"
    "- Respond ONLY with a JSON object mapping each category name to its answer, "
    "no extra text"
)

_PT_BR_ARTICLES = ("O ", "A ", "Os ", "As ", "Um ", "Uma ", "Uns ", "Umas ")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 1


def _strip_leading_article(text: str) -> str:
    """Remove a leading pt-BR article if present (case-insensitive)."""
    upper = text.upper()
    for article in _PT_BR_ARTICLES:
        if upper.startswith(article.upper()):
            return text[len(article):]
    return text


def _build_user_prompt(letter: str, categories: list[dict]) -> str:
    """Build the user-facing prompt with the round letter and category list."""
    names = [cat["full_name"] for cat in categories]
    return (
        f'Letter: {letter}\n'
        f'Categories: {json.dumps(names, ensure_ascii=False)}\n\n'
        f'Respond with a JSON object mapping each category name to an answer '
        f'starting with "{letter}".'
    )


def _parse_and_validate(raw: str, letter: str, categories: list[dict]) -> dict[str, str]:
    """Parse AI response JSON and map category names back to input IDs."""
    data = json.loads(raw)

    name_to_id = {cat["full_name"]: cat["input_id"] for cat in categories}

    answers: dict[str, str] = {}
    upper_letter = letter.upper()

    for name, answer in data.items():
        input_id = name_to_id.get(name)
        if input_id is None:
            # Fuzzy match: AI may shorten or rephrase category names
            name_lower = name.lower()
            for cat_name, cat_id in name_to_id.items():
                if cat_id not in answers and (
                    name_lower in cat_name.lower()
                    or cat_name.lower() in name_lower
                ):
                    input_id = cat_id
                    break
        if input_id is None:
            logger.warning(f"Categoria desconhecida na resposta da IA: '{name}'")
            continue

        answer = str(answer).strip()
        answer = _strip_leading_article(answer)

        if not answer.upper().startswith(upper_letter):
            logger.warning(
                f"Resposta '{answer}' não começa com '{letter}' — descartada"
            )
            continue

        if len(answer) > 20:
            answer = answer[:20]

        answers[input_id] = answer

    return answers


async def generate_answers(
    letter: str,
    categories: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict[str, str]:
    """
    Call OpenAI to generate StopotS answers for each category.

    Returns a dict mapping input_id -> answer, ready for fill_all_categories().
    On failure returns an empty dict so the bot never crashes.
    """
    config = load_config()
    api_key = config.get("openai_api_key")
    if not api_key:
        logger.error("API Key não configurada — insira a chave e clique em Salvar")
        return {}

    model = config.get("model", model)
    client = AsyncOpenAI(api_key=api_key)
    user_prompt = _build_user_prompt(letter, categories)

    for attempt in range(1 + MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=512,
            )

            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("```", 1)[0].strip()

            answers = _parse_and_validate(raw, letter, categories)
            logger.info(f"IA gerou {len(answers)}/{len(categories)} respostas")
            return answers

        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                logger.warning("JSON inválido da IA — tentando novamente...")
                continue
            logger.error("JSON inválido da IA após retentativa — retornando vazio")
            return {}

        except AuthenticationError:
            logger.error("API Key inválida — verifique a chave informada")
            raise InvalidAPIKeyError()

        except RateLimitError:
            logger.error("Sem créditos ou limite de requisições atingido na API")
            return {}

        except Exception as e:
            logger.error(f"Erro na chamada à API: {e}")
            return {}
