#  Foodgram - ваш продуктовый помошник 


### Описание проекта
На данном сайте можно публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», также скачивать список покупок для приготовления выбранных блюд.

#### Технологи:

- Python 3.9
- Django 3.2.3
- Django Rest Framework 3.12.4
- Djoser 2.2.0
- Gunicorn 20.1.0


### Как запустить проект 

-Клонировать репозиторий

-Установить Docker и Docker Compose
`sudo apt install docker-ce docker-compose -y`

-Cоздайте .env файл как в .env.example

-Запуск контейнера:

`docker-compose up -d`

-Заполнение базы данными:

`sudo docker-compose exec backend python manage.py collectstatic --no-input`

`sudo docker compose -f docker-compose.yml exec backend cp -r /app/collected_static/. /app/static/`

`sudo docker-compose exec backend python manage.py migrate`

`sudo docker-compose exec backend python manage.py import_ingredients`

 Admin

  password: 236716

  login: gor1911@mail.ru

  доступен тут: http://foodgram1911.ddns.net/

### Автор :

[Багдасарян Гор ](https://github.com/Gor1911)