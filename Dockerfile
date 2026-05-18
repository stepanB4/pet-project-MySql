# Используем официальный легковесный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл со списком зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Копируем весь код приложения в контейнер
COPY . .

# Указываем порт, который будет слушать приложение
EXPOSE 8000

# Команда для запуска с помощью Gunicorn (производственный сервер)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]