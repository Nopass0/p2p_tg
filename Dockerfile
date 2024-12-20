# Используем официальный образ Python 3.10
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл requirements.txt в контейнер
COPY requirements.txt .

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем содержимое текущей директории в рабочую директорию контейнера
COPY . .

# Запускаем Flask-приложение на порту 9000 через Python
CMD ["python", "app.py"]

# Выставляем переменную окружения для Flask (не обязательно, если используем app.py напрямую)
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
