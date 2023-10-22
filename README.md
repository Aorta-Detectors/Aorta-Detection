# Aorta-Detection
Это основной репозиторий для практики в СПБГУ.    
Пока что реализована логика для регистрации и входа на приватную страницу.    
Чтобы запустить проект:

 * нужно установить `docker`.
 * Далее нужно создать `.env` файл на основе `.env-example`, возможно, подредактировать настройки, какие хотите (почему сразу не класть `.env` файл? Для безопасности. Там будут лежать важные пароли и другие чувствительные данные, поэтому в общем репо их хранить не будем, только моковый пример). 
 * Далее необходимо в терминале прописать команду `docker compose up` и немного подождать. Поднимется и web приложение (на `http://localhost:8000/`) и база данных (PostgreSQL).    

Логика работы пока простая: при логине приложение пишет в ваш браузер cookie с токеном, который позволяет вас индентифицировать при каждом обращении к API. Для безопасности токен по умолчанию самоуничтожится через 30 минут после логина, и приложение упадет с ошибкой (это надо пофиксить, отловить ошибку, и, например, выбросить юзера обратно на страницу с логином с соответствующим сообщением).