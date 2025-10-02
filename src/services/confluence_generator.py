"""
Генератор отчетов для Confluence
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import ReportGenerator, CommitData, TaskData, MetadataChanges
from .constants import METADATA_ELEMENT_TYPES, TABLE_STYLES, STYLE_SETTINGS


class ConfluenceReportGenerator(ReportGenerator):
    """Генератор отчетов для Confluence"""
    
    def __init__(self, gitlab_url: str, gitlab_group: str, gitlab_project: str):
        self.gitlab_url = gitlab_url
        self.gitlab_group = gitlab_group
        self.gitlab_project = gitlab_project
    
    def generate(self, commits: List[CommitData], tasks: List[TaskData], 
                metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует HTML отчет в формате Confluence"""
        html = f'''
        <h1>Отчет о релизе - {datetime.now().strftime("%Y-%m-%d %H:%M")}</h1>
        '''
        
        # Статистика по авторам
        author_stats = self._calculate_author_stats(commits)
        
        # Таблица коммитов по задачам
        html += self._generate_commits_table(commits, tasks)
        
        # Общая статистика
        html += self._generate_general_stats(commits, tasks, metadata)
        
        # Таблица статистики авторов
        html += self._generate_author_stats_table(author_stats)
        
        # Раздел метаданных
        if metadata and metadata.has_changes:
            html += self._generate_metadata_section(metadata)
        
        return html
    
    def _calculate_author_stats(self, commits: List[CommitData]) -> Dict[str, Dict[str, int]]:
        """Вычисляет статистику по авторам"""
        author_stats = {}
        for commit in commits:
            author = commit.author
            if author not in author_stats:
                author_stats[author] = {'total_lines': 0, 'task_count': 0}
            author_stats[author]['total_lines'] += commit.total_lines
            if commit.task_number:
                author_stats[author]['task_count'] += 1
        return author_stats
    
    def _generate_general_stats(self, commits: List[CommitData], tasks: List[TaskData], metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует общую статистику"""
        total_lines = sum(commit.total_lines for commit in commits)
        
        html = '''
        <h2>Общая статистика</h2>
        <table border="{}" style="border-collapse: {}; width: {};">
            <tr>
                <th>Показатель</th>
                <th>Значение</th>
            </tr>
            <tr>
                <td>Количество коммитов</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Количество задач</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>Общее количество строк кода</td>
                <td>{}</td>
            </tr>
        '''.format(
            TABLE_STYLES['border'],
            TABLE_STYLES['border_collapse'],
            TABLE_STYLES['width'],
            len(commits),
            len(tasks),
            total_lines
        )
        
        # Добавляем статистику метаданных, если есть изменения
        if metadata and metadata.has_changes and metadata.summary:
            total_metadata_changes = (metadata.summary.get('total_added', 0) + 
                                    metadata.summary.get('total_removed', 0) + 
                                    metadata.summary.get('total_modified', 0))
            
            html += f'''
            <tr>
                <td>Изменений метаданных</td>
                <td>{total_metadata_changes}</td>
            </tr>
            <tr>
                <td>Добавлено элементов метаданных</td>
                <td>{metadata.summary.get('total_added', 0)}</td>
            </tr>
            <tr>
                <td>Удалено элементов метаданных</td>
                <td>{metadata.summary.get('total_removed', 0)}</td>
            </tr>
            <tr>
                <td>Изменено элементов метаданных</td>
                <td>{metadata.summary.get('total_modified', 0)}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _generate_commits_table(self, commits: List[CommitData], tasks: List[TaskData]) -> str:
        """Генерирует таблицу коммитов по задачам"""
        html = '''
        <h2>Коммиты по задачам</h2>
        <table border="{}" style="border-collapse: {}; width: {};">
            <tr>
                <th>Задача</th>
                <th>Автор</th>
                <th>Статус</th>
                <th>Строк кода</th>
                <th>Сообщение коммита</th>
                <th>Задача интрасервис</th>
                <th>Страницы Confluence</th>
            </tr>
        '''.format(
            TABLE_STYLES['border'],
            TABLE_STYLES['border_collapse'],
            TABLE_STYLES['width']
        )
        
        for commit in commits:
            task_info = self._find_task_info(commit.task_number, tasks)
            status = self._format_status(task_info.get('status', 'Unknown'))
            confluence_pages_html = self._format_confluence_pages(task_info.get('confluence_pages', []))
            
            # Формируем информацию о задаче интрасервис
            intraservice_html = ""
            if task_info.get('intraservice_task'):
                intraservice_task = task_info.get('intraservice_task')
                intraservice_url = task_info.get('intraservice_task_url')
                if intraservice_url:
                    intraservice_html = f'<a href="{intraservice_url}" target="_blank">{intraservice_task}</a>'
                else:
                    intraservice_html = intraservice_task
            
            task_link = self._format_task_link(commit.task_number)
            commit_link = self._format_commit_link(commit)
            
            html += f'''
            <tr>
                <td>{task_link}</td>
                <td>{commit.author}</td>
                <td>{status}</td>
                <td>{commit.total_lines}</td>
                <td>{commit_link}</td>
                <td>{intraservice_html}</td>
                <td>{confluence_pages_html}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _generate_author_stats_table(self, author_stats: Dict[str, Dict[str, int]]) -> str:
        """Генерирует таблицу статистики авторов"""
        html = '''
        <h2>Статистика авторов</h2>
        <table border="{}" style="border-collapse: {}; width: {};">
            <tr>
                <th>Автор</th>
                <th>Строк кода (Всего)</th>
                <th>Количество коммитов</th>
            </tr>
        '''.format(
            TABLE_STYLES['border'],
            TABLE_STYLES['border_collapse'],
            TABLE_STYLES['width']
        )
        
        for author, stats in author_stats.items():
            html += f'''
            <tr>
                <td>{author}</td>
                <td>{stats['total_lines']}</td>
                <td>{stats['task_count']}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _generate_metadata_section(self, metadata: MetadataChanges) -> str:
        """Генерирует раздел метаданных"""
        total_changes = 0
        if metadata.summary:
            total_changes = (metadata.summary.get('total_added', 0) + 
                           metadata.summary.get('total_removed', 0) + 
                           metadata.summary.get('total_modified', 0))
        
        html = f'''
        <h2>📋 Изменения метаданных подсистемы</h2>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p><strong>📄 Файл:</strong> src/cf/Configuration.xml</p>
            <p><strong>📅 Период:</strong> с {metadata.since_commit_date or 'Неизвестно'} по {metadata.current_commit_date or 'Неизвестно'}</p>
            <p><strong>📊 Всего изменений:</strong> {total_changes}</p>
        </div>
        '''
        
        # Сводка изменений
        if metadata.summary:
            html += f'''
        <div style="background-color: {STYLE_SETTINGS['metadata_summary_bg']}; padding: {STYLE_SETTINGS['metadata_summary_padding']}; margin: {STYLE_SETTINGS['metadata_summary_margin']}; border-radius: {STYLE_SETTINGS['metadata_summary_border_radius']};">
            <h3>📊 Сводка изменений</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #e9ecef;">
                    <th style="padding: 8px;">Тип изменения</th>
                    <th style="padding: 8px;">Количество</th>
                    <th style="padding: 8px;">Цветовая индикация</th>
                </tr>
                <tr>
                    <td style="padding: 8px;">➕ Добавлено элементов</td>
                    <td style="padding: 8px; text-align: center; font-weight: bold; color: #28a745;">{metadata.summary.get('total_added', 0)}</td>
                    <td style="padding: 8px; background-color: #d4edda;"></td>
                </tr>
                <tr>
                    <td style="padding: 8px;">➖ Удалено элементов</td>
                    <td style="padding: 8px; text-align: center; font-weight: bold; color: #dc3545;">{metadata.summary.get('total_removed', 0)}</td>
                    <td style="padding: 8px; background-color: #f8d7da;"></td>
                </tr>
                <tr>
                    <td style="padding: 8px;">✏️ Изменено элементов</td>
                    <td style="padding: 8px; text-align: center; font-weight: bold; color: #ffc107;">{metadata.summary.get('total_modified', 0)}</td>
                    <td style="padding: 8px; background-color: #fff3cd;"></td>
                </tr>
            </table>
        </div>
        '''
        
        # Детали изменений
        html += self._generate_metadata_tables(metadata)
        
        return html
    
    def _generate_metadata_tables(self, metadata: MetadataChanges) -> str:
        """Генерирует таблицы с деталями изменений метаданных"""
        html = ""
        
        # Добавленные элементы
        if metadata.added_metadata:
            html += self._generate_metadata_table("Добавленные элементы", metadata.added_metadata)
        
        # Удаленные элементы
        if metadata.removed_metadata:
            html += self._generate_metadata_table("Удаленные элементы", metadata.removed_metadata)
        
        # Измененные элементы
        if metadata.modified_metadata:
            html += self._generate_metadata_table("Измененные элементы", metadata.modified_metadata)
        
        return html
    
    def _generate_metadata_table(self, title: str, elements: List[Any]) -> str:
        """Генерирует таблицу для элементов метаданных"""
        # Определяем цветовую схему в зависимости от типа изменений
        color_scheme = {
            "Добавленные элементы": {"color": "#28a745", "bg": "#d4edda", "icon": "➕"},
            "Удаленные элементы": {"color": "#dc3545", "bg": "#f8d7da", "icon": "➖"},
            "Измененные элементы": {"color": "#ffc107", "bg": "#fff3cd", "icon": "✏️"}
        }
        
        scheme = color_scheme.get(title, {"color": "#6c757d", "bg": "#f8f9fa", "icon": "📝"})
        
        html = f'''
        <h3 style="color: {scheme['color']};">{scheme['icon']} {title} ({len(elements)})</h3>
        <table border="{TABLE_STYLES['border']}" style="border-collapse: {TABLE_STYLES['border_collapse']}; width: {TABLE_STYLES['width']};">
            <tr style="background-color: #e9ecef;">
                <th style="padding: 8px;">Тип</th>
                <th style="padding: 8px;">Имя</th>
                <th style="padding: 8px;">Путь</th>
                <th style="padding: 8px;">Детали</th>
            </tr>
        '''
        
        for element in elements:
            elem_type = METADATA_ELEMENT_TYPES.get(element.tag, element.tag)
            elem_name = element.text if hasattr(element, 'text') else element.get('text', '')
            elem_path = element.path if hasattr(element, 'path') else element.get('path', '')
            
            # Дополнительная информация
            details = []
            if hasattr(element, 'children_count'):
                details.append(f"Дочерних элементов: {element.children_count}")
            if hasattr(element, 'attributes') and element.attributes:
                details.append(f"Атрибутов: {len(element.attributes)}")
            if hasattr(element, 'changes') and element.changes:
                details.append(f"Изменения: {', '.join(element.changes)}")
            
            details_str = "<br>".join(details) if details else "—"
            
            html += f'''
            <tr style="background-color: {scheme['bg']};">
                <td style="padding: 8px; font-weight: bold; color: {scheme['color']};">{elem_type}</td>
                <td style="padding: 8px;">{elem_name}</td>
                <td style="padding: 8px; font-size: 0.9em; color: #6c757d;">{elem_path or '—'}</td>
                <td style="padding: 8px; font-size: 0.9em;">{details_str}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _find_task_info(self, task_number: Optional[str], tasks: List[TaskData]) -> Dict[str, Any]:
        """Находит информацию о задаче по номеру"""
        if not task_number or not tasks:
            return {}
        
        for task in tasks:
            if task.task_number == task_number:
                return {
                    'status': task.status,
                    'confluence_pages': task.confluence_pages or [],
                    'intraservice_task': task.intraservice_task,
                    'intraservice_task_url': task.intraservice_task_url
                }
        return {}
    
    def _format_status(self, status: str) -> str:
        """Форматирует статус задачи"""
        if status == 'ReadyToWork':
            return "Создана"
        return status
    
    def _format_confluence_pages(self, pages: List[Dict[str, str]]) -> str:
        """Форматирует список страниц Confluence"""
        if not pages:
            return "Нет"
        
        confluence_links = []
        for page in pages:
            confluence_links.append(f'<a href="{page["url"]}" target="_blank">{page["filename"]}</a>')
        return '<br>'.join(confluence_links)
    
    def _format_task_link(self, task_number: Optional[str]) -> str:
        """Форматирует ссылку на задачу"""
        if not task_number:
            return 'Неопределено'
        
        # Доработка
        return task_number
    
    def _format_commit_link(self, commit: CommitData) -> str:
        """Форматирует ссылку на коммит"""
        commit_url = f'{self.gitlab_url}/{self.gitlab_group}/{self.gitlab_project}/-/commit/{commit.id}'
        message = commit.message[:500]
        if len(commit.message) > 500:
            message += "..."
        return f'<a href="{commit_url}">{message}</a>'
