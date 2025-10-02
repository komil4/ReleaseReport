"""
Конфигурация логирования для системы отчетов
"""
import logging
import sys
from typing import Optional
from datetime import datetime


class ReportLogger:
    """Настроенный логгер для системы отчетов"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """Получает настроенный логгер"""
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(level)
            
            # Удаляем существующие обработчики
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            # Создаем форматтер
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Консольный обработчик
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Файловый обработчик
            file_handler = logging.FileHandler(
                f'report_system_{datetime.now().strftime("%Y%m%d")}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Отключаем распространение на корневой логгер
            logger.propagate = False
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def setup_root_logger(cls, level: int = logging.INFO) -> None:
        """Настраивает корневой логгер"""
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(
                    f'report_system_{datetime.now().strftime("%Y%m%d")}.log',
                    encoding='utf-8'
                )
            ]
        )


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Получает логгер для указанного имени"""
    return ReportLogger.get_logger(name, level)


def setup_logging(level: int = logging.INFO) -> None:
    """Настраивает систему логирования"""
    ReportLogger.setup_root_logger(level)
