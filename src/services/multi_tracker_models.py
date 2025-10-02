"""
Модели для поддержки множественных таск-трекеров
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class TaskTrackerType(Enum):
    """Типы таск-трекеров"""
    JIRA = "jira"
    ONEC = "onec"
    NONE = "none"


@dataclass
class TaskTrackerConfig:
    """Конфигурация отдельного таск-трекера"""
    name: str  # Уникальное имя трекера
    type: TaskTrackerType
    enabled: bool
    config: Dict[str, Any]  # Специфичная конфигурация трекера
    priority: int = 0  # Приоритет (чем меньше, тем выше приоритет)
    description: Optional[str] = None


@dataclass
class MultiTrackerConfig:
    """Конфигурация множественных таск-трекеров"""
    trackers: List[TaskTrackerConfig]
    deduplication_enabled: bool = True
    merge_strategy: str = "priority"  # priority, first_found, merge_all
    timeout_seconds: int = 30  # Таймаут для запросов к трекерам


@dataclass
class TaskSearchResult:
    """Результат поиска задачи в конкретном трекере"""
    tracker_name: str
    tracker_type: TaskTrackerType
    task_data: Dict[str, Any]
    found: bool
    error: Optional[str] = None
    response_time_ms: Optional[int] = None


@dataclass
class MultiTaskResult:
    """Результат поиска задач во всех трекерах"""
    task_number: str
    results: List[TaskSearchResult]
    primary_result: Optional[TaskSearchResult] = None
    merged_data: Optional[Dict[str, Any]] = None
    found_in_trackers: List[str] = None
    
    def __post_init__(self):
        if self.found_in_trackers is None:
            self.found_in_trackers = [
                result.tracker_name for result in self.results 
                if result.found
            ]


@dataclass
class TaskDeduplicationInfo:
    """Информация о дедупликации задач"""
    task_number: str
    found_in_trackers: List[str]
    primary_tracker: str
    deduplication_reason: str
    merged_fields: List[str] = None
