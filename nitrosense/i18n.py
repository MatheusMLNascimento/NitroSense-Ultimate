"""
Simple i18n manager for NitroSense Ultimate.
Provides JSON-backed translations and runtime locale switching.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtCore import QLocale

from .core.logger import logger

_LOCALE_MANAGER = None


def _normalize_lang(lang: str) -> str:
    if not lang or lang.lower() in ("auto", "system"):
        locale = QLocale.system().name() or "en"
    else:
        locale = lang

    locale = locale.replace('-', '_')
    locale = locale.strip()

    if locale.lower().startswith("pt"):
        return "pt_BR"
    if locale.lower().startswith("en"):
        return "en"
    if "_" in locale:
        primary = locale.split("_")[0]
        if primary.lower() == "pt":
            return "pt_BR"
        if primary.lower() == "en":
            return "en"
    return "en"


class I18nManager:
    """Translation manager backed by JSON locale files."""

    LOCALES_DIR = Path(__file__).resolve().parent / "locales"
    DEFAULT_LANGUAGE = "en"
    SUPPORTED_LANGUAGES = {"en", "pt_BR"}

    def __init__(self, language: str = "auto"):
        self.language = _normalize_lang(language)
        self.messages = self._load_language(self.language)

    def _load_language(self, language: str) -> Dict[str, str]:
        locale_file = self.LOCALES_DIR / f"{language}.json"
        if not locale_file.exists():
            logger.warning(f"Translation file not found for '{language}', falling back to '{self.DEFAULT_LANGUAGE}'")
            if language != self.DEFAULT_LANGUAGE:
                return self._load_language(self.DEFAULT_LANGUAGE)
            return {}

        try:
            with locale_file.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.error(f"Failed to load translation file {locale_file}: {exc}")
            return {}

    def gettext(self, message: str) -> str:
        return self.messages.get(message, message)

    def set_language(self, language: str) -> None:
        self.language = _normalize_lang(language)
        self.messages = self._load_language(self.language)

    def available_languages(self):
        return sorted(self.SUPPORTED_LANGUAGES)


def initialize_i18n(language: str = "auto") -> I18nManager:
    global _LOCALE_MANAGER
    _LOCALE_MANAGER = I18nManager(language)
    logger.info(f"i18n initialized with language: {_LOCALE_MANAGER.language}")
    return _LOCALE_MANAGER


def get_i18n_manager() -> I18nManager:
    global _LOCALE_MANAGER
    if _LOCALE_MANAGER is None:
        _LOCALE_MANAGER = I18nManager("auto")
    return _LOCALE_MANAGER


def t(message: str) -> str:
    return get_i18n_manager().gettext(message)
