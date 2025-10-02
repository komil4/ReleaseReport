"""
Сервис для работы с множественными таск-трекерами
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseService, ServiceError
from .multi_tracker_models import (
    MultiTrackerConfig, TaskTrackerConfig, TaskSearchResult, 
    MultiTaskResult, TaskDeduplicationInfo, TaskTrackerType
)
from .task_service_factory import TaskServiceFactory
from .logger_config import get_logger


class MultiTrackerService(BaseService):
    """Сервис для работы с множественными таск-трекерами"""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)

        self.multi_tracker_config = self.config_manager.get_multi_tracker_config()
        self.logger = get_logger(self.__class__.__name__)
        self.tracker_services = {}
        self._initialize_trackers()
    
    def _initialize_trackers(self) -> None:
        """Инициализирует все настроенные трекеры"""
        for tracker_config in self.multi_tracker_config.trackers:
            if not tracker_config.enabled:
                self.logger.info(f"Tracker '{tracker_config.name}' is disabled, skipping")
                continue
            
            try:
                # Создаем временный конфиг-сервис для этого трекера
                service = TaskServiceFactory.create_task_service(tracker_config)
                self.tracker_services[tracker_config.name] = {
                    'service': service,
                    'config': tracker_config,
                    'type': tracker_config.type
                }
                self.logger.info(f"Initialized tracker '{tracker_config.name}' of type {tracker_config.type.value}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize tracker '{tracker_config.name}': {str(e)}")
                # Продолжаем работу с другими трекерами
    
    def _create_temp_config_manager(self, tracker_config: TaskTrackerConfig):
        """Создает временный конфиг-сервис для конкретного трекера"""
        class TempConfigService:
            def __init__(self, tracker_config):
                self.tracker_config = tracker_config
            
            def get_active_task_tracker_type(self):
                return tracker_config.type.value
            
            def is_task_tracker_enabled(self):
                return tracker_config.enabled
            
            def get_task_tracker_config(self):
                return {
                    'type': tracker_config.type.value,
                    'enabled': tracker_config.enabled,
                    **tracker_config.config
                }
            
            def get_jira_config(self):
                if tracker_config.type == TaskTrackerType.JIRA:
                    return tracker_config.config
                return {}
            
            def get_confluence_config(self):
                return self.config_manager.get_confluence_config() if hasattr(self, 'config_manager') else {}
        
        temp_config = TempConfigService(tracker_config)
        temp_config.config_manager = self.config_manager
        return temp_config
    

    def get_task_details(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Получает детали задач из всех трекеров"""
        if not task_numbers:
            return []
        
        self.logger.info(f"Searching for {len(task_numbers)} tasks across {len(self.tracker_services)} trackers")
        
        # Получаем результаты из всех трекеров параллельно
        all_results = self._search_tasks_parallel(task_numbers)
        
        # Обрабатываем результаты
        processed_results = self._process_multi_tracker_results(all_results)
        
        # Дедуплицируем если включено
        if self.multi_tracker_config.deduplication_enabled:
            processed_results = self._deduplicate_tasks(processed_results)
        
        self.logger.info(f"Found {len(processed_results)} unique tasks")
        return processed_results
    
    def get_task_trackers_info(self):
        """Возвращает информацию о трекерах в формате, совместимом с фронтендом"""
        if not self.tracker_services:
            return {
                'type': 'none',
                'enabled': False,
                'message': 'No trackers configured',
                'trackers': []
            }
        
        # Получаем активные трекеры
        active_trackers = []
        for tracker_name, tracker_info in self.tracker_services.items():
            if tracker_info['config'].enabled:
                active_trackers.append({
                    'name': tracker_name,
                    'type': tracker_info['type'].value,
                    'enabled': True,
                    'message': 'Active'
                })
        
        # Если есть активные трекеры, возвращаем информацию о них
        if active_trackers:
            if len(active_trackers) == 1:
                # Один трекер - возвращаем в старом формате для совместимости
                return {
                    'type': active_trackers[0]['type'],
                    'enabled': True,
                    'message': f"Active tracker: {active_trackers[0]['name']}",
                    'trackers': active_trackers
                }
            else:
                # Несколько трекеров - возвращаем список
                return {
                    'type': 'multiple',
                    'enabled': True,
                    'message': f"Active trackers: {len(active_trackers)}",
                    'trackers': active_trackers
                }
        else:
            return {
                'type': 'none',
                'enabled': False,
                'message': 'No active trackers',
                'trackers': []
            }
    
    def get_tracker_status(self) -> Dict[str, Any]:
        """Возвращает детальный статус всех трекеров"""
        if not self.tracker_services:
            return {
                'total_trackers': 0,
                'active_trackers': 0,
                'trackers': [],
                'message': 'No trackers configured'
            }
        
        trackers_status = []
        active_count = 0
        
        for tracker_name, tracker_info in self.tracker_services.items():
            tracker_status = {
                'name': tracker_name,
                'type': tracker_info['type'].value,
                'enabled': tracker_info['config'].enabled,
                'priority': tracker_info['config'].priority,
                'description': tracker_info['config'].description or '',
                'status': 'Active' if tracker_info['config'].enabled else 'Disabled'
            }
            trackers_status.append(tracker_status)
            
            if tracker_info['config'].enabled:
                active_count += 1
        
        return {
            'total_trackers': len(self.tracker_services),
            'active_trackers': active_count,
            'trackers': trackers_status,
            'message': f'{active_count} of {len(self.tracker_services)} trackers active'
        }

    def _search_tasks_parallel(self, task_numbers: List[str]) -> Dict[str, List[TaskSearchResult]]:
        """Поиск задач во всех трекерах параллельно"""
        all_results = {task_number: [] for task_number in task_numbers}
        
        # Используем ThreadPoolExecutor для параллельного выполнения
        with ThreadPoolExecutor(max_workers=len(self.tracker_services)) as executor:
            # Создаем задачи для каждого трекера
            future_to_tracker = {}
            for tracker_name, tracker_info in self.tracker_services.items():
                future = executor.submit(
                    self._search_tasks_in_tracker,
                    tracker_name,
                    tracker_info,
                    task_numbers
                )
                future_to_tracker[future] = tracker_name
            
            # Собираем результаты
            for future in as_completed(future_to_tracker):
                tracker_name = future_to_tracker[future]
                try:
                    tracker_results = future.result()
                    for task_number, result in tracker_results.items():
                        all_results[task_number].append(result)
                except Exception as e:
                    self.logger.error(f"Error in tracker '{tracker_name}': {str(e)}")
                    # Добавляем ошибку для всех задач
                    for task_number in task_numbers:
                        all_results[task_number].append(TaskSearchResult(
                            tracker_name=tracker_name,
                            tracker_type=TaskTrackerType.NONE,
                            task_data={},
                            found=False,
                            error=str(e)
                        ))
        
        return all_results
    
    def _search_tasks_in_tracker(self, tracker_name: str, tracker_info: Dict[str, Any], 
                                task_numbers: List[str]) -> Dict[str, TaskSearchResult]:
        """Поиск задач в конкретном трекере"""
        results = {}
        service = tracker_info['service']
        tracker_type = tracker_info['type']
        
        start_time = time.time()
        
        try:
            # Получаем детали задач
            task_details = service.get_task_details(task_numbers)
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Создаем результаты для найденных задач
            found_task_numbers = {task.get('task_number') for task in task_details}
            
            for task_number in task_numbers:
                if task_number in found_task_numbers:
                    # Найдена задача
                    task_data = next(
                        (task for task in task_details if task.get('task_number') == task_number),
                        {}
                    )
                    results[task_number] = TaskSearchResult(
                        tracker_name=tracker_name,
                        tracker_type=tracker_type,
                        task_data=task_data,
                        found=True,
                        response_time_ms=response_time
                    )
                else:
                    # Задача не найдена
                    results[task_number] = TaskSearchResult(
                        tracker_name=tracker_name,
                        tracker_type=tracker_type,
                        task_data={},
                        found=False,
                        response_time_ms=response_time
                    )
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Error searching in tracker '{tracker_name}': {str(e)}")
            
            # Создаем результаты с ошибкой для всех задач
            for task_number in task_numbers:
                results[task_number] = TaskSearchResult(
                    tracker_name=tracker_name,
                    tracker_type=tracker_type,
                    task_data={},
                    found=False,
                    error=str(e),
                    response_time_ms=response_time
                )
        
        return results
    
    def _process_multi_tracker_results(self, all_results: Dict[str, List[TaskSearchResult]]) -> List[MultiTaskResult]:
        """Обрабатывает результаты из всех трекеров"""
        processed_results = []
        
        for task_number, results in all_results.items():
            # Определяем основной результат
            primary_result = self._determine_primary_result(results)
            
            # Объединяем данные если нужно
            merged_data = self._merge_task_data(results) if primary_result else None
            
            multi_result = MultiTaskResult(
                task_number=task_number,
                results=results,
                primary_result=primary_result,
                merged_data=merged_data
            )
            
            processed_results.append(multi_result)
        
        return processed_results
    
    def _determine_primary_result(self, results: List[TaskSearchResult]) -> Optional[TaskSearchResult]:
        """Определяет основной результат на основе стратегии"""
        found_results = [r for r in results if r.found]
        
        if not found_results:
            return None
        
        if self.multi_tracker_config.merge_strategy == "priority":
            # Выбираем по приоритету трекера
            tracker_priorities = {
                tracker_config.name: tracker_config.priority 
                for tracker_config in self.multi_tracker_config.trackers
            }
            
            return min(found_results, key=lambda r: tracker_priorities.get(r.tracker_name, 999))
        
        elif self.multi_tracker_config.merge_strategy == "first_found":
            # Выбираем первый найденный
            return found_results[0]
        
        else:  # merge_all
            # Возвращаем первый для объединения
            return found_results[0]
    
    def _merge_task_data(self, results: List[TaskSearchResult]) -> Dict[str, Any]:
        """Объединяет данные задач из разных трекеров"""
        found_results = [r for r in results if r.found]
        
        if not found_results:
            return {}
        
        if len(found_results) == 1:
            return found_results[0].task_data
        
        # Объединяем данные, приоритет у трекеров с меньшим приоритетом
        tracker_priorities = {
            tracker_config.name: tracker_config.priority 
            for tracker_config in self.multi_tracker_config.trackers
        }
        
        sorted_results = sorted(found_results, key=lambda r: tracker_priorities.get(r.tracker_name, 999))
        
        merged_data = {}
        merged_fields = []
        
        for result in sorted_results:
            for key, value in result.task_data.items():
                if key not in merged_data or not merged_data[key]:
                    merged_data[key] = value
                    if key not in merged_fields:
                        merged_fields.append(key)
        
        # Добавляем информацию о трекерах
        merged_data['_trackers'] = [r.tracker_name for r in found_results]
        merged_data['_merged_fields'] = merged_fields
        
        return merged_data
    
    def _deduplicate_tasks(self, results: List[MultiTaskResult]) -> List[Dict[str, Any]]:
        """Дедуплицирует задачи по номеру"""
        task_map = {}
        deduplication_info = []
        
        for result in results:
            if not result.primary_result:
                continue
            
            task_number = result.task_number
            
            if task_number in task_map:
                # Задача уже найдена, выбираем лучший результат
                existing_result = task_map[task_number]
                
                if self._is_better_result(result, existing_result):
                    task_map[task_number] = result
                    deduplication_info.append(TaskDeduplicationInfo(
                        task_number=task_number,
                        found_in_trackers=result.found_in_trackers,
                        primary_tracker=result.primary_result.tracker_name,
                        deduplication_reason="Better result found"
                    ))
                else:
                    deduplication_info.append(TaskDeduplicationInfo(
                        task_number=task_number,
                        found_in_trackers=result.found_in_trackers,
                        primary_tracker=existing_result.primary_result.tracker_name,
                        deduplication_reason="Existing result is better"
                    ))
            else:
                task_map[task_number] = result
        
        # Логируем информацию о дедупликации
        if deduplication_info:
            self.logger.info(f"Deduplication applied to {len(deduplication_info)} tasks")
            for info in deduplication_info:
                self.logger.debug(f"Task {info.task_number}: {info.deduplication_reason}")
        
        # Возвращаем данные задач
        return [
            result.merged_data or result.primary_result.task_data
            for result in task_map.values()
        ]
    
    def _is_better_result(self, new_result: MultiTaskResult, existing_result: MultiTaskResult) -> bool:
        """Определяет, является ли новый результат лучше существующего"""
        # Сравниваем по приоритету трекеров
        tracker_priorities = {
            tracker_config.name: tracker_config.priority 
            for tracker_config in self.multi_tracker_config.trackers
        }
        
        new_priority = tracker_priorities.get(new_result.primary_result.tracker_name, 999)
        existing_priority = tracker_priorities.get(existing_result.primary_result.tracker_name, 999)
        
        return new_priority < existing_priority
    
