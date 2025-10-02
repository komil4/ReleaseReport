from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
from datetime import datetime
from src.services.report_service import ReportService
from src.services.config_manager import ConfigManager
from src.services.logger_config import setup_logging

app = FastAPI(title="Release Report API", version="1.0.0")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Модели данных
class UpdateDateRequest(BaseModel):
    date: str

class GenerateReportRequest(BaseModel):
    report_date: str = None

def get_services():
    # Настраиваем логирование
    setup_logging()
    
    # Создаем менеджер конфигурации
    config_manager = ConfigManager()
    
    # Создаем сервис отчетов
    report_service = ReportService(config_manager)
    return report_service

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница с кнопкой для генерации отчета"""
    # Читаем актуальную дату из файла commits
    current_date = "Не определена"
    try:
        if os.path.exists("commits"):
            with open("commits", "r", encoding="utf-8") as f:
                commit_data = f.read().strip()
                if commit_data:
                    # Парсим дату из формата ISO
                    try:
                        dt = datetime.fromisoformat(commit_data.replace('Z', '+00:00'))
                        current_date = dt.strftime("%d.%m.%Y %H:%M:%S")
                    except:
                        current_date = commit_data
    except Exception as e:
        print(f"Ошибка чтения файла commits: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_date": current_date
    })

@app.post("/generate-report")
async def generate_report(request: GenerateReportRequest = None):
    """Генерирует отчет по коммитам и создает страницу в Confluence"""
    try:
        report_service = get_services()
        
        # Если передана дата формирования отчета, используем её
        if request and request.report_date:
            result = await report_service.generate_report_with_date(request.report_date)
        else:
            result = await report_service.generate_report()
        
        # Возвращаем JSON с информацией об отчете и URL страницы
        return {
            "status": "success", 
            "message": "Отчет успешно сформирован", 
            "data": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/preview-report", response_class=HTMLResponse)
async def preview_report(report_date: str = None):
    """Генерирует предварительный просмотр отчета без сохранения в Confluence"""
    try:
        report_service = get_services()
        
        # Если передана дата формирования отчета, используем её
        if report_date:
            result = await report_service.generate_preview_report_with_date(report_date)
        else:
            result = await report_service.generate_preview_report()
        
        # Возвращаем HTML страницу с отчетом
        return HTMLResponse(content=result, status_code=200)
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Ошибка формирования отчета</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
                .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; border: 1px solid #f5c6cb; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>Ошибка при формировании отчета</h2>
                <p>{str(e)}</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

@app.get("/task-tracker-info")
async def get_task_tracker_info():
    """Возвращает информацию о текущих таск-трекерах"""
    try:
        report_service = get_services()
        info = report_service.get_task_tracker_info()
        return {
            "status": "success",
            "data": info
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/multi-tracker-status")
async def get_multi_tracker_status():
    """Возвращает детальную информацию о множественных трекерах"""
    try:
        report_service = get_services()
        data_manager = report_service.data_manager
        
        if data_manager.multi_task_service:
            status = data_manager.multi_task_service.get_tracker_status()
            return {
                "status": "success",
                "data": status
            }
        else:
            return {
                "status": "success",
                "data": {
                    "message": "Multi-tracker service not enabled",
                    "single_tracker_info": data_manager.get_task_tracker_info()
                }
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Страница настроек конфигурации"""
    return templates.TemplateResponse("config.html", {
        "request": request
    })

@app.get("/api/config")
async def get_config():
    """Получает текущую конфигурацию"""
    try:
        config_manager = ConfigManager()
        config_data = config_manager.get_all_config()
        return {
            "status": "success",
            "data": config_data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/config")
async def save_config(config_data: dict):
    """Сохраняет конфигурацию"""
    try:
        config_manager = ConfigManager()
        
        # Создаем резервную копию
        config_manager.backup_config()
        
        # Сохраняем каждый раздел конфигурации
        if 'app' in config_data:
            config_manager.create_config_file('app.json', {'app': config_data['app']})
        
        if 'gitlab' in config_data:
            config_manager.create_config_file('gitlab.json', {'gitlab': config_data['gitlab']})
        
        if 'confluence' in config_data:
            config_manager.create_config_file('confluence.json', {'confluence': config_data['confluence']})
        
        if 'trackers' in config_data:
            config_manager.create_config_file('trackers.json', {'trackers': config_data['trackers']})
        
        # Перезагружаем конфигурацию
        config_manager.reload_config()
        
        return {
            "status": "success",
            "message": "Конфигурация успешно сохранена"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/update-commit-date")
async def update_commit_date(request: UpdateDateRequest):
    """Обновляет дату в файле commits"""
    try:
        # Валидация даты
        try:
            # Парсим дату в формате YYYY-MM-DDTHH:MM
            dt = datetime.fromisoformat(request.date)
        except ValueError:
            return {
                "status": "error", 
                "message": "Неверный формат даты. Используйте формат YYYY-MM-DDTHH:MM"
            }
        
        # Конвертируем в ISO формат с Z в конце
        iso_date = dt.isoformat() + 'Z'
        
        # Записываем в файл commits
        with open("commits", "w", encoding="utf-8") as f:
            f.write(iso_date)
        
        # Форматируем дату для отображения
        formatted_date = dt.strftime("%d.%m.%Y %H:%M:%S")
        
        return {
            "status": "success",
            "message": "Дата успешно обновлена",
            "data": {
                "formatted_date": formatted_date,
                "iso_date": iso_date
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при обновлении даты: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)