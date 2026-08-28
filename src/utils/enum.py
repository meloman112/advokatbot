from enum import StrEnum


class LogLevelEnum(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LanguageEnum(StrEnum):
    RU = "ru"
    UZ = "uz"


class RequestStatusEnum(StrEnum):
    NEW = "new"
    ANSWERED = "answered"
