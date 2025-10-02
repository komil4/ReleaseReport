"""
Рефакторенный сервис отчетов
"""
from typing import Dict, Any, Optional
import logging
from .base import BaseService, ServiceError
from .data_manager import DataManager
from .html_generator import HTMLReportGenerator
from .confluence_generator import ConfluenceReportGenerator
from .confluence_service import ConfluenceService
from .multi_tracker_service import MultiTrackerService
from .config_manager import ConfigManager
from .constants import MESSAGES


class ReportService(BaseService):
    """Рефакторенный сервис отчетов"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.config_manager = config_manager
        self.data_manager = DataManager(config_manager)
        self.html_generator = HTMLReportGenerator()
        self.confluence_service = ConfluenceService(config_manager)
        self.multi_tracker_service = MultiTrackerService(config_manager)
        
        # Получаем конфигурацию для Confluence генератора
        gitlab_config = config_manager.get_gitlab_config()
                
        self.confluence_generator = ConfluenceReportGenerator(
            gitlab_url=gitlab_config['url'],
            gitlab_group=gitlab_config['group'],
            gitlab_project=gitlab_config['project']
        )
    
    async def generate_report(self) -> Dict[str, Any]:
        """Генерирует полный отчет и сохраняет в Confluence"""
        try:
            # Получаем данные
            last_commit = self.data_manager.get_last_commit()
            report_data = self.data_manager.get_report_data(last_commit)
            
            if not report_data['has_data']:
                return {
                    'message': report_data['message'],
                    'page_url': None,
                    'commits_count': 0,
                    'tasks_count': 0,
                    'metadata_changes': False
                }
            
            # Создаем страницу в Confluence
            page_url = self.confluence_service.create_report_page(
                commit_data=report_data['commits'],
                task_data=report_data['tasks'],
                report_service=self,
                metadata_changes=report_data['metadata']
            )
            
            # Сохраняем последний коммит
            latest_commit = self.data_manager.get_latest_commit()
            if latest_commit:
                self.data_manager.save_last_commit(latest_commit)
            
            return {
                'message': 'Report generated successfully',
                'commits_count': len(report_data['commits']),
                'tasks_count': len(report_data['tasks']),
                'metadata_changes': report_data['metadata'] is not None,
                'page_url': page_url
            }
            
        except Exception as e:
            self._handle_error(e, "generating report")
    
    async def generate_report_with_date(self, report_date: str) -> Dict[str, Any]:
        """Генерирует полный отчет с указанной датой формирования и сохраняет в Confluence"""
        try:
            from datetime import datetime
            
            # Парсим дату формирования отчета
            try:
                report_dt = datetime.fromisoformat(report_date)
            except ValueError:
                raise ServiceError(f"Неверный формат даты: {report_date}")
            
            # Получаем данные с фильтрацией по дате
            last_commit = self.data_manager.get_last_commit()
            report_data = self.data_manager.get_report_data_with_date_filter(last_commit, report_dt)
            
            if not report_data['has_data']:
                return {
                    'message': report_data['message'],
                    'page_url': None,
                    'commits_count': 0,
                    'tasks_count': 0,
                    'metadata_changes': False
                }
            
            # Создаем страницу в Confluence
            page_url = self.confluence_service.create_report_page(
                commit_data=report_data['commits'],
                task_data=report_data['tasks'],
                report_service=self,
                metadata_changes=report_data['metadata']
            )
            
            # Сохраняем указанную дату формирования в файл commits
            iso_date = report_dt.isoformat() + 'Z'
            self.data_manager.save_last_commit(iso_date)
            
            return {
                'message': 'Report generated successfully',
                'commits_count': len(report_data['commits']),
                'tasks_count': len(report_data['tasks']),
                'metadata_changes': report_data['metadata'] is not None,
                'page_url': page_url
            }
            
        except Exception as e:
            self._handle_error(e, "generating report with date")
    
    async def generate_preview_report_with_date(self, report_date: str) -> str:
        """Генерирует HTML отчет для предварительного просмотра с указанной датой"""
        try:
            from datetime import datetime
            
            # Парсим дату формирования отчета
            try:
                report_dt = datetime.fromisoformat(report_date)
            except ValueError:
                raise ServiceError(f"Неверный формат даты: {report_date}")
            
            # Получаем данные с фильтрацией по дате
            last_commit = self.data_manager.get_last_commit()
            report_data = self.data_manager.get_report_data_with_date_filter(last_commit, report_dt)
            
            if not report_data['has_data']:
                return self.html_generator.generate_empty_report(report_data['message'])
            
            # Генерируем HTML
            return self.html_generator.generate(
                commits=report_data['commits'],
                tasks=report_data['tasks'],
                metadata=report_data['metadata']
            )
            
        except Exception as e:
            self.logger.error(f"Error generating preview report with date: {str(e)}")
            return self.html_generator.generate_error_report(f'Ошибка при формировании отчета: {str(e)}')
    
    def generate_confluence_html_report(self, commit_data: list, task_data: list, metadata_changes: Optional[Dict[str, Any]] = None) -> str:
        """Генерирует HTML отчет в формате Confluence (для обратной совместимости)"""
        try:
            # Преобразуем данные в типизированные объекты
            commits = self._convert_commits_data(commit_data)
            tasks = self._convert_tasks_data(task_data)
            metadata = self._convert_metadata_data(metadata_changes)
            
            # Генерируем отчет
            return self.confluence_generator.generate(commits, tasks, metadata)
            
        except Exception as e:
            self.logger.error(f"Error generating Confluence HTML report: {str(e)}")
            raise ServiceError(f"Failed to generate Confluence HTML report: {str(e)}")
    
    def _convert_commits_data(self, commit_data: list) -> list:
        """Преобразует данные коммитов в типизированные объекты"""
        from .validators import DataValidator
        from .base import CommitData
        
        # Если список пустой, возвращаем его как есть
        if not commit_data:
            return commit_data
        
        # Если данные уже являются объектами CommitData, возвращаем их как есть
        if isinstance(commit_data[0], CommitData):
            return commit_data
        
        # Иначе валидируем и преобразуем из словарей
        return DataValidator.validate_commit_data(commit_data)
    
    def _convert_tasks_data(self, task_data: list) -> list:
        """Преобразует данные задач в типизированные объекты"""
        from .validators import DataValidator
        from .base import TaskData
        
        # Если список пустой, возвращаем его как есть
        if not task_data:
            return task_data
        
        # Если данные уже являются объектами TaskData, возвращаем их как есть
        if isinstance(task_data[0], TaskData):
            return task_data
        
        # Иначе валидируем и преобразуем из словарей
        return DataValidator.validate_task_data(task_data)
    
    def _convert_metadata_data(self, metadata_changes: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Преобразует данные метаданных в типизированные объекты"""
        if not metadata_changes:
            return None
        
        from .validators import DataValidator
        from .base import MetadataChanges
        
        # Если данные уже являются объектом MetadataChanges, возвращаем его как есть
        if isinstance(metadata_changes, MetadataChanges):
            return metadata_changes
        
        # Иначе валидируем и преобразуем из словаря
        return DataValidator.validate_metadata_changes(metadata_changes)
    
    def get_task_tracker_info(self) -> Dict[str, Any]:
        """Возвращает информацию о таск-трекере"""
        return self.data_manager.get_task_tracker_info()
    
    def get_last_commit(self) -> Optional[str]:
        """Получает последний обработанный коммит"""
        return self.data_manager.get_last_commit()
    
    def save_last_commit(self, commit_hash: str) -> None:
        """Сохраняет последний обработанный коммит"""
        self.data_manager.save_last_commit(commit_hash)
