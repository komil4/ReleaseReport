"""
Фабрика для создания генераторов отчетов
"""
from typing import Dict, Any
from .base import ReportGenerator, ReportType
from .html_generator import HTMLReportGenerator
from .confluence_generator import ConfluenceReportGenerator


class ReportGeneratorFactory:
    """Фабрика для создания генераторов отчетов"""
    
    _generators = {
        ReportType.HTML_PREVIEW: HTMLReportGenerator,
        ReportType.CONFLUENCE: ConfluenceReportGenerator,
    }
    
    @classmethod
    def create_generator(cls, report_type: ReportType, **kwargs) -> ReportGenerator:
        """Создает генератор отчетов указанного типа"""
        if report_type not in cls._generators:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        generator_class = cls._generators[report_type]
        
        # Для Confluence генератора передаем дополнительные параметры
        if report_type == ReportType.CONFLUENCE:
            required_params = ['jira_url', 'gitlab_url', 'gitlab_group', 'gitlab_project']
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"Missing required parameter for Confluence generator: {param}")
            return generator_class(**kwargs)
        
        return generator_class()
    
    @classmethod
    def get_available_types(cls) -> list:
        """Возвращает список доступных типов генераторов"""
        return list(cls._generators.keys())
    
    @classmethod
    def register_generator(cls, report_type: ReportType, generator_class: type) -> None:
        """Регистрирует новый тип генератора"""
        if not issubclass(generator_class, ReportGenerator):
            raise ValueError("Generator class must inherit from ReportGenerator")
        cls._generators[report_type] = generator_class
