"""
Базовые классы и интерфейсы для системы отчетов
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from .logger_config import get_logger


class ReportType(Enum):
    """Типы отчетов"""
    CONFLUENCE = "confluence"
    HTML_PREVIEW = "html_preview"


class TaskTrackerType(Enum):
    """Типы таск-трекеров"""
    JIRA = "jira"
    ONEC = "onec"
    NONE = "none"


@dataclass
class CommitData:
    """Данные коммита"""
    id: str
    message: str
    author: str
    date: str
    task_number: Optional[str] = None
    total_lines: int = 0
    url: Optional[str] = None


@dataclass
class TaskData:
    """Данные задачи"""
    task_number: str
    summary: str
    description: str
    status: str
    priority: str
    url: str
    confluence_pages: List[Dict[str, str]] = None
    intraservice_task: Optional[str] = None
    intraservice_task_url: Optional[str] = None


@dataclass
class MetadataElement:
    """Элемент метаданных"""
    id: str
    tag: str
    text: str
    attributes: Dict[str, str]
    path: str


@dataclass
class MetadataChanges:
    """Изменения метаданных"""
    has_changes: bool
    since_commit_date: Optional[str] = None
    current_commit_date: Optional[str] = None
    added_metadata: List[MetadataElement] = None
    removed_metadata: List[MetadataElement] = None
    modified_metadata: List[MetadataElement] = None
    summary: Dict[str, int] = None


class BaseService(ABC):
    """Базовый класс для всех сервисов"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = get_logger(self.__class__.__name__)
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """Обработка ошибок с логированием"""
        error_msg = f"Error in {self.__class__.__name__}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        self.logger.error(error_msg)
        raise error


class ReportGenerator(ABC):
    """Абстрактный класс для генераторов отчетов"""
    
    @abstractmethod
    def generate(self, commits: List[CommitData], tasks: List[TaskData], 
                metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует отчет"""
        pass


class DataProvider(ABC):
    """Абстрактный класс для поставщиков данных"""
    
    @abstractmethod
    def get_data(self, **kwargs) -> Any:
        """Получает данные"""
        pass


class ValidationError(Exception):
    """Ошибка валидации данных"""
    pass


class ConfigurationError(Exception):
    """Ошибка конфигурации"""
    pass


class ServiceError(Exception):
    """Ошибка сервиса"""
    pass
