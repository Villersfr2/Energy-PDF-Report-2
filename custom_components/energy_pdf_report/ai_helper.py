"""Utilities to orchestrate AI-powered advice for the PDF report."""

from __future__ import annotations

import asyncio
import logging
from typing import Final

import aiohttp

FALLBACK_MESSAGE: Final[str] = "La fonction n’est pas active actuellement."

_LOGGER = logging.getLogger(__name__)

_SYSTEM_PROMPTS: Final[dict[str, str]] = {
    "fr": (
        "Tu es un consultant énergie expert des environnements industriels et tertiaires. "
        "Tes recommandations doivent être professionnelles, actionnables et adaptées à un public B2B. "
        "Rédige systématiquement ta réponse en français."
    ),
    "en": (
        "You are an energy management consultant supporting industrial and commercial clients. "
        "Your recommendations must stay professional, actionable, and tailored for B2B decision makers. "
        "Always answer in English."
    ),
    "nl": (
        "Je bent een energieconsultant voor zakelijke omgevingen en grote gebouwen. "
        "Je adviezen moeten professioneel, uitvoerbaar en gericht op een B2B-publiek zijn. "
        "Antwoord altijd in het Nederlands."
    ),
}

_USER_INSTRUCTIONS: Final[dict[str, str]] = {
    "fr": (
        "Conclusion du rapport ci-dessous. Formule un conseil professionnel, orienté B2B, "
        "en t’appuyant sur les constats fournis."
    ),
    "en": (
        "The following report conclusion summarises the situation. Provide a professional, B2B-oriented "
        "piece of advice based on it."
    ),
    "nl": (
        "Onderstaande conclusie vat het rapport samen. Formuleer één professioneel B2B-advies op basis daarvan."
    ),
}

_API_URL: Final[str] = "https://api.openai.com/v1/chat/completions"


async def generate_advice(conclusion: str, api_key: str | None, language: str) -> str:
    """Générer un conseil professionnel personnalisé depuis OpenAI."""

    normalized_api_key = (api_key or "").strip()
    conclusion_text = (conclusion or "").strip()

    if not normalized_api_key:
        return FALLBACK_MESSAGE

    if not conclusion_text:
        return FALLBACK_MESSAGE

    system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["fr"])
    user_instruction = _USER_INSTRUCTIONS.get(language, _USER_INSTRUCTIONS["fr"])

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Conclusion :\n{conclusion_text}\n\nInstruction : {user_instruction}",
            },
        ],
        "temperature": 0.6,
        "max_tokens": 600,
    }

    headers = {
        "Authorization": f"Bearer {normalized_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=25)
        ) as session:
            async with session.post(
                _API_URL,
                json=payload,
                headers=headers,
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    _LOGGER.warning(
                        "OpenAI API error (status: %s): %s", response.status, body
                    )
                    return FALLBACK_MESSAGE

                data = await response.json()
    except asyncio.TimeoutError:
        _LOGGER.warning("OpenAI API request timed out")
        return FALLBACK_MESSAGE
    except aiohttp.ClientError as err:
        _LOGGER.warning("OpenAI API request failed: %s", err)
        return FALLBACK_MESSAGE

    try:
        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content")
    except (KeyError, IndexError, TypeError):
        _LOGGER.warning("Unexpected OpenAI API response structure: %s", data)
        return FALLBACK_MESSAGE

    if isinstance(content, str):
        advice = content.strip()
    elif isinstance(content, list):
        advice_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text_part = item.get("text")
                if isinstance(text_part, str):
                    advice_parts.append(text_part)
        advice = "".join(advice_parts).strip()
    else:
        advice = ""

    if not advice:
        return FALLBACK_MESSAGE

    return advice


__all__ = ["generate_advice", "FALLBACK_MESSAGE"]
