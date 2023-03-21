# Выберите базовый образ Python
FROM python:3.10

# Установите рабочую директорию
WORKDIR /app

# Копируйте файлы с требованиями и установите зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируйте остальные файлы с кодом бота
COPY . .

# Запустите бота при старте контейнера
CMD ["python", "hodor.py"]
