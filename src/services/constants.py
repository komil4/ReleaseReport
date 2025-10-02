"""
Константы для системы отчетов
"""

# HTML константы
HTML_TEMPLATES = {
    'DOCTYPE': '<!DOCTYPE html>',
    'META_CHARSET': '<meta charset="UTF-8">',
    'META_VIEWPORT': '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
}

# CSS классы
CSS_CLASSES = {
    'container': 'container',
    'header': 'header',
    'content': 'content',
    'section': 'section',
    'stats': 'stats',
    'stat_card': 'stat-card',
    'stat_number': 'stat-number',
    'stat_label': 'stat-label',
    'commits_list': 'commits-list',
    'commit_item': 'commit-item',
    'commit_hash': 'commit-hash',
    'commit_message': 'commit-message',
    'commit_meta': 'commit-meta',
    'task_link': 'task-link',
    'tasks_list': 'tasks-list',
    'task_item': 'task-item',
    'task_title': 'task-title',
    'task_description': 'task-description',
    'task_meta': 'task-meta',
    'footer': 'footer',
    'no_data': 'no-data',
}

# Типы элементов метаданных 1С
METADATA_ELEMENT_TYPES = {
    '{http://v8.1c.ru/8.3/MDClasses}Catalog': 'Справочник',
    '{http://v8.1c.ru/8.3/MDClasses}Document': 'Документ',
    '{http://v8.1c.ru/8.3/MDClasses}InformationRegister': 'Регистр сведений',
    '{http://v8.1c.ru/8.3/MDClasses}AccumulationRegister': 'Регистр накоплений',
    '{http://v8.1c.ru/8.3/MDClasses}Constant': 'Константа',
}

# Пути к файлам
FILE_PATHS = {
    'commits_file': 'commits',
    'configuration_xml': 'src/cf/Configuration.xml',
}

# Сообщения
MESSAGES = {
    'no_commits': 'Нет новых коммитов для отображения',
    'no_tasks': 'Нет задач для отображения',
    'no_metadata_changes': 'Нет изменений в метаданных подсистемы',
    'report_generated': 'Отчет сформирован автоматически системой генерации отчетов релизов',
    'warning_no_task_service': 'Warning: No task service available, skipping task details',
    'warning_metadata_analysis': 'Warning: Could not analyze metadata changes',
}

# Ошибки
ERRORS = {
    'confluence_config_missing': 'Confluence configuration is missing',
    'error_creating_page': 'Error creating Confluence page',
    'error_generating_report': 'Error generating report',
    'error_analyzing_metadata': 'Error analyzing metadata changes',
    'error_reading_commits': 'Error reading last commit',
    'error_saving_commits': 'Error saving last commit',
}

# Настройки таблиц
TABLE_STYLES = {
    'border': '1',
    'border_collapse': 'collapse',
    'width': '100%',
}

# Настройки стилей
STYLE_SETTINGS = {
    'metadata_summary_bg': '#f0f0f0',
    'metadata_summary_padding': '10px',
    'metadata_summary_margin': '10px 0',
    'metadata_summary_border_radius': '5px',
}
