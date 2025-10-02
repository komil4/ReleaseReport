"""
Сервис для получения данных Confluence, связанных с задачами
"""
import re
from typing import List, Dict, Any, Optional
from .base import BaseService
from .confluence_service import ConfluenceService
from .logger_config import get_logger


class ConfluenceDataService(BaseService):
    """Сервис для получения данных Confluence, связанных с задачами"""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.logger = get_logger(self.__class__.__name__)
        
        # Инициализируем ConfluenceService только если конфигурация доступна
        try:
            self.confluence_service = ConfluenceService(config_manager)
            self.enabled = True
            self.logger.info("Confluence data service initialized successfully")
        except Exception as e:
            self.logger.warning(f"Confluence data service disabled: {str(e)}")
            self.confluence_service = None
            self.enabled = False
    
    def enrich_tasks_with_confluence_data(self, tasks: List[Dict[str, Any]], 
                                        jira_service=None) -> List[Dict[str, Any]]:
        """
        Обогащает задачи данными Confluence
        
        Args:
            tasks: Список задач для обогащения
            jira_service: Опциональный JiraService для получения дополнительных данных
            
        Returns:
            Список задач с добавленными данными Confluence
        """
        if not self.enabled or not self.confluence_service:
            self.logger.info("Confluence data service is disabled, skipping enrichment")
            return tasks
        
        enriched_tasks = []
        
        for task in tasks:
            try:
                # Получаем данные Confluence для задачи
                confluence_pages = self._get_confluence_pages_for_task(task, jira_service)
                
                # Создаем обогащенную задачу
                enriched_task = task.copy()
                enriched_task['confluence_pages'] = confluence_pages
                
                enriched_tasks.append(enriched_task)
                
            except Exception as e:
                self.logger.error(f"Error enriching task {task.get('task_number', 'unknown')} with Confluence data: {str(e)}")
                # В случае ошибки возвращаем исходную задачу
                enriched_tasks.append(task)
        
        self.logger.info(f"Enriched {len(enriched_tasks)} tasks with Confluence data")
        return enriched_tasks
    
    def _get_confluence_pages_for_task(self, task: Dict[str, Any], 
                                     jira_service=None) -> List[Dict[str, str]]:
        """
        Получает страницы Confluence, связанные с задачей
        
        Args:
            task: Данные задачи
            jira_service: Опциональный JiraService для получения дополнительных данных
            
        Returns:
            Список страниц Confluence
        """
        confluence_pages = []
        
        try:
            # Получаем данные из описания задачи
            description_pages = self._extract_confluence_pages_from_text(
                task.get('description', '')
            )
            confluence_pages.extend(description_pages)
            
            # Если есть JiraService, получаем дополнительные данные из Jira
            if jira_service and hasattr(jira_service, 'jira'):
                jira_pages = self._get_confluence_pages_from_jira(
                    task.get('task_number', ''), 
                    jira_service
                )
                confluence_pages.extend(jira_pages)
            
            # Удаляем дубликаты по URL
            confluence_pages = self._deduplicate_confluence_pages(confluence_pages)
            
        except Exception as e:
            self.logger.error(f"Error getting Confluence pages for task {task.get('task_number', 'unknown')}: {str(e)}")
        
        return confluence_pages
    
    def _extract_confluence_pages_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Извлекает ссылки на Confluence из текста
        
        Args:
            text: Текст для поиска ссылок
            
        Returns:
            Список страниц Confluence
        """
        confluence_pages = []
        
        if not text:
            return confluence_pages
        
        try:
            # Ищем ссылки на Confluence
            confluence_urls = re.findall(
                r'https?://[^/]*confluence[^/]*/[^\s<>"\']*', 
                text
            )
            
            for url in confluence_urls:
                # Очищаем URL от лишних параметров
                clean_url = self._clean_confluence_url(url)
                
                if clean_url:
                    page_title = self._get_page_title_by_url(clean_url)
                    
                    confluence_pages.append({
                        'filename': page_title,
                        'url': clean_url,
                        'created': 'Unknown',
                        'author': 'Unknown',
                        'source': 'description'
                    })
        
        except Exception as e:
            self.logger.error(f"Error extracting Confluence pages from text: {str(e)}")
        
        return confluence_pages
    
    def _get_confluence_pages_from_jira(self, task_number: str, 
                                      jira_service) -> List[Dict[str, str]]:
        """
        Получает страницы Confluence из Jira задачи
        
        Args:
            task_number: Номер задачи Jira
            jira_service: Сервис Jira
            
        Returns:
            Список страниц Confluence
        """
        confluence_pages = []
        
        try:
            issue = jira_service.jira.issue(task_number)
            
            # Получаем все прикрепления к задаче
            attachments = issue.fields.attachment
            if attachments:
                for attachment in attachments:
                    if (hasattr(attachment, 'filename') and 
                        attachment.filename and 
                        ('confluence' in attachment.filename.lower() or 
                         attachment.filename.endswith('.html') or
                         attachment.filename.endswith('.htm'))):
                        
                        confluence_pages.append({
                            'filename': attachment.filename,
                            'url': attachment.content,
                            'created': attachment.created,
                            'author': attachment.author.displayName if hasattr(attachment, 'author') else 'Unknown',
                            'source': 'attachment'
                        })
            
            # Ищем ссылки в связях задачи
            if hasattr(issue.fields, 'issuelinks') and issue.fields.issuelinks:
                for link in issue.fields.issuelinks:
                    link_fields = []
                    if hasattr(link, 'outwardIssue') and hasattr(link.outwardIssue.fields, 'summary'):
                        link_fields.append(link.outwardIssue.fields.summary)
                    if hasattr(link, 'inwardIssue') and hasattr(link.inwardIssue.fields, 'summary'):
                        link_fields.append(link.inwardIssue.fields.summary)
                    if hasattr(link, 'comment') and link.comment:
                        link_fields.append(link.comment)
                    
                    for field_text in link_fields:
                        if field_text:
                            text_pages = self._extract_confluence_pages_from_text(str(field_text))
                            for page in text_pages:
                                page['source'] = 'issue_link'
                            confluence_pages.extend(text_pages)
        
        except Exception as e:
            self.logger.error(f"Error getting Confluence pages from Jira task {task_number}: {str(e)}")
        
        return confluence_pages
    
    def _clean_confluence_url(self, url: str) -> str:
        """
        Очищает URL Confluence от лишних параметров
        
        Args:
            url: Исходный URL
            
        Returns:
            Очищенный URL
        """
        try:
            # Обрезаем ссылку до pageId=число, если есть
            pageid_match = re.search(r'(pageId=\d+)', url)
            if pageid_match:
                # Оставляем только до pageId=число
                clean_url = re.sub(r'(pageId=\d+).*', r'\1', url)
                # Восстанавливаем ссылку до pageId=число
                clean_url = url[:url.find(pageid_match.group(1)) + len(pageid_match.group(1))]
                return clean_url
            else:
                return url
        except Exception as e:
            self.logger.error(f"Error cleaning Confluence URL {url}: {str(e)}")
            return url
    
    def _get_page_title_by_url(self, url: str) -> str:
        """
        Получает заголовок страницы Confluence по URL
        
        Args:
            url: URL страницы Confluence
            
        Returns:
            Заголовок страницы
        """
        try:
            if self.confluence_service and hasattr(self.confluence_service, 'get_page_title_by_url'):
                return self.confluence_service.get_page_title_by_url(url)
            else:
                return 'Confluence Page'
        except Exception as e:
            self.logger.error(f"Error getting page title for URL {url}: {str(e)}")
            return 'Confluence Page'
    
    def _deduplicate_confluence_pages(self, pages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Удаляет дубликаты страниц Confluence по URL
        
        Args:
            pages: Список страниц Confluence
            
        Returns:
            Список уникальных страниц
        """
        seen_urls = set()
        unique_pages = []
        
        for page in pages:
            url = page.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_pages.append(page)
        
        return unique_pages
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервис"""
        return self.enabled
