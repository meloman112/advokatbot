from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import aiofiles

from src.utils.enum import LanguageEnum

ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent

TEXTS_DIR: Final[Path] = ROOT_DIR / "texts"


async def load_json_text(lang: str = LanguageEnum.RU) -> Any:
    if lang not in tuple(LanguageEnum):
        lang = LanguageEnum.RU
    async with aiofiles.open(file=TEXTS_DIR / f"{lang}.json", encoding="utf-8") as f:
        text = await f.read()
        return json.loads(text)
