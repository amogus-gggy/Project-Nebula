"""
Модуль для работы с шаблонами Jinja2.
"""
import os
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .responses import HTMLResponse


class Jinja2Templates:
    """
    Класс для управления шаблонами Jinja2.
    
    Пример использования:
        templates = Jinja2Templates(directory="templates")
        
        @app.get("/")
        async def home(request):
            return templates.TemplateResponse("index.html", {"request": request, "title": "Home"})
    """
    
    def __init__(self, directory: Union[str, os.PathLike], **env_options):
        """
        Инициализация шаблонов Jinja2.
        
        Args:
            directory: Путь к директории с шаблонами
            **env_options: Дополнительные параметры для Jinja2 Environment
        """
        try:
            from jinja2 import Environment, FileSystemLoader
        except ImportError:
            raise ImportError("Jinja2 не установлен. Установите: pip install jinja2")
        
        self.directory = str(directory)
        
        # Настройки по умолчанию
        default_options = {
            "loader": FileSystemLoader(self.directory),
            "autoescape": True,
        }
        default_options.update(env_options)
        
        self.env = Environment(**default_options)
    
    def TemplateResponse(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> "TemplateResponse":
        """
        Рендерит шаблон и возвращает TemplateResponse.
        
        Args:
            name: Имя файла шаблона
            context: Контекст для рендеринга
            status_code: HTTP статус код
            headers: HTTP заголовки
            
        Returns:
            TemplateResponse объект
        """
        return TemplateResponse(
            name=name,
            context=context or {},
            templates=self,
            status_code=status_code,
            headers=headers,
        )


class TemplateResponse(HTMLResponse):
    """
    Ответ с отрендеренным HTML-шаблоном.
    """

    def __init__(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        templates: Optional[Jinja2Templates] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.context = context or {}
        self.templates = templates

        # Рендерим шаблон
        template = templates.env.get_template(name)
        content = template.render(**self.context)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
        )


def render_template(
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    templates_directory: Union[str, os.PathLike] = "templates",
    **jinja_options: Any,
) -> str:
    """
    Функция для рендеринга шаблона Jinja2.
    
    Args:
        template_name: Имя файла шаблона
        context: Контекст для рендеринга
        templates_directory: Путь к директории с шаблонами
        **jinja_options: Дополнительные параметры для Jinja2
        
    Returns:
        Отрендеренная HTML-строка
        
    Пример:
        @app.get("/")
        async def home(request):
            html = render_template("index.html", {"title": "Home"})
            return HTMLResponse(html)
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        raise ImportError("Jinja2 не установлен. Установите: pip install jinja2")
    
    templates = Environment(
        loader=FileSystemLoader(str(templates_directory)),
        autoescape=True,
        **jinja_options,
    )
    
    template = templates.get_template(template_name)
    return template.render(context or {})
