Telegram-бот для конвертации разных видов маркировки системы "Честный знак"
Как запустить:
1) Интерпретатор Python должен быть установлен в системе.
2) Клонируем или качаем и распаковываем этот репозиторий в любую директорию.
3) Создаём бота через BotFather (https://t.me/BotFather), получаем api-key, и копируем его в файл 'key.py', предварительно создав его в одной директории с файлом 'tg_adapter.py'.
4) Качаем и распаковываем архив (https://drive.google.com/file/d/1GKw7m3H7ZiVigjqHALNgxHMDznZZyShy/view?usp=sharing) в ту же директорию, то есть 'data' должна находиться в том же месте, где и 'tg_adapter.py'.
Должна получиться такая структура:
.
├── Dockerfile
├── csv_handler.py
├── data
│   ├── demo_samples
├── data.zip
├── db_adapter.py
├── extract_datamatrix_concurrent.py
├── key.py
├── label_generation.py
├── requirements.txt
├── tg_adapter.py

6) С помощью консоли перейдём в директорию:
   cd {repo-name}
7) Создадим виртуальное окружения для python:
   python3 -m venv venv
8)  Активируем окружение:
   для Windows:
    venv\Scripts\activate
  для macOS/Linux:
   source venv/bin/activate
9) Установим зависимости:
    pip install -r requirements.txt
10) Запускаем скрипт tg_adapter.py:
    python tg_adapter.py
