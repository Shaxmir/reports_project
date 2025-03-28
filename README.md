# Telegram Бот для учёта продаж, расходов и кассы

## Описание
Этот бот помогает вести учёт продаж и расходов, формировать отчёты и анализировать финансы.  

## Функционал
- **Добавление продаж** (`/sale`)
- **Добавление расходов** (`/expense`)
- **Просмотр отчета за сегодня** (`/report`)
- **Поиск продаж/расходов за дату** (`/search`)
- **Просмотр старых отчетов** (`/report_by_date`)  
- **Просмотр отчета за месяц (Графики и анализ)** (`/monthly_report`)  
- **Продажи за сегодня** (`/all_sales`)  
- **Создать отчет в PDF файле** (`/report_pdf`)  
- **Пополнение кассы** (`/cash`)  
- **Изменение расходов** (`/expenses`)  
- **Изменение продаж** (`/sales`)  
- **Просмотр своего User_ID** (`/myid`)  

## 🛠 Установка и запуск

1. **Склонировать репозиторий**
   ```commandline
   git clone https://github.com/Shaxmir/reports_project.git
   cd reports_project
    ```

2. **Создайте виртуальное окружение и активируйте его:**
    ```commandline
    Python: `python -m venv .venv`
    Linux/MacOS: `source .venv/bin/activate`
    Windows: `.venv\Scripts\activate`
    ```

3. **Установите зависимости:** 
    ```commandline
    pip install -r requirements.txt
    ```

4. **Настройте переменные окружения:**  
   Создайте файл `.env` и укажите в нем необходимые переменные, например:
    ```commandline
    BOT_TOKEN=0
    CREATOR_ID=0
    ADMIN_IDS=0,0
    ```

5. **Выполните миграции базы данных:** 
    ```commandline
    python manage.py migrate
    ```

6. **Создайте суперпользователя (администратора) Django:** 
    ```commandline
    python manage.py createsuperuser
    ``` 

7. **Запустите Django-cервер:** 
    ```commandline
    python manage.py runserver
    ``` 
      
8. **Запустите бота:** 
    ```commandline
    python manage.py bot.py
    ```

## Требования

- Python + Django – основа проекта

- aiogram 3.x – работа с Telegram

- PostgreSQL – база данных

- Matplotlib – построение графиков


## Server setup

```shell
git clone https://github.com/Shaxmir/reports_project.git
cd reports_project

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt 
nano .env

sudo nano /etc/systemd/system/django.service
sudo nano /etc/systemd/system/bot.service

sudo systemctl start django.service
sudo systemctl start bot.service

sudo systemcrl restart django
sudo systemcrl restart bot

sudo systemcrl status django
sudo systemcrl status bot

sudo journalctl -u bot.service -f
```


### server .env
```text 
BOT_TOKEN=0
CREATOR_ID=0
ADMIN_IDS=0,0
```

## Проект

- sales_reports - Сам проект, все настройки тут
- reports - Функционал бота
    - reports/handlers - все хендлеры бота здесь
    - reports/filters - фильтры для ролей
