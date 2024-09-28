
# Демо-видео: 
[demo_eps2pdf](https://drive.google.com/file/d/1nuYZzZGK_ig8Yq_j2Lfmn1HzqlPSMrMj/view?usp=drive_link), [demo_help_json](https://drive.google.com/file/d/1pDw9doz5UjWZkHsJQ5EN-XBZukx6-Vwc/view?usp=drive_link)

# **Telegram-бот для конвертации разных видов маркировки**
Как запустить:
1) Docker должен быть установлен ([Docker Desktop для Windows](https://docs.docker.com/desktop/install/windows-install/))
2) Загружаем [Docker image](https://drive.google.com/file/d/1zIc5n7WLXzZS8sP9EbSPmVg0ANyJh201/view?usp=drive_link)
3) Загружаем и распаковываем куда-нибудь [архив](https://drive.google.com/file/d/1GKw7m3H7ZiVigjqHALNgxHMDznZZyShy/view?usp=sharing), создаём где-нибудь файл 'logs.txt'
4) Создаём бота через [BotFather](https://t.me/BotFather), получаем api-key
5) Импортируем загруженный Docker image:
`docker load -i C:\path\to\image.tar.gz`
6) Создаём и запускаем контейнер из образа, заменяя TELEGRAM_TOKEN, пути к каталогу data, файлу logs.txt и image_name на соответствующие :
 `docker run -d --name matrix_tags -e TELEGRAM_TOKEN="YOUR_API_KEY" --mount type=bind,source=/your/path/to/data,target=/python-docker/data --mount type=bind,source=/your/path/to/logs.txt,target=/python-docker/logs.txt --restart=unless-stopped image_name`

~~При самостоятельной сборке нужен ghostscript и шрифт DejaVu Serif в venv/lib/python3.11/site-packages/reportlab/fonts~~

