# MedCabinet

## 1. Установка

1. Распаковать в нужную директорию, например `/home/user/`

2. Создать виртуальное окружение:
   ```bash
   python3 -m venv venv
   
3. Активировать виртуальное окружение:
	```bash
	source venv/bin/activate
	
4. Установить зависимости
	```bash
	pip install -r requirements.txt
	
## 2. Настройка конфигурации

1. Переименовать файл app/core/config.py.example в app/core/config.py и заполнить нужные значения (шаг 3).

## 3. Получение ключа для Google Custom Search API

### Получение API_KEY

1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)

2. Войти в свой аккаунт Google.

3. Создать новый проект или выбрать существующий.

4. В меню слева перейти в API и сервисы → Библиотека.

5. Найти и включить Custom Search API (или "API пользовательского поиска").

6. Перейти в API и сервисы → Учётные данные.

7. Нажать Создать ключ API и получить ключ.

8. Сохранить ключ в app/core/config.py в параметре:
	```bash
	API_KEY = "YOUR_API_KEY"
	
### Получение CX

1. Открыть [Google Programmable Search Engine](https://cse.google.com/cse/all)

2. Создать новый поисковик, нажав Добавить.

3. В поле Сайты для поиска можно указать *.google.com (для поиска по всем сайтам) или оставить пустым (после создания включить поиск по всему интернету в настройках).

4. После создания перейти в Панель управления → Идентификатор поисковой системы.

5. Получить CX и сохранить в app/core/config.py:
	```bash
	CX = "YOUR_CX"
	
## 4. Запуск службой (systemd)

1. Создать файл службы:
	```bash
	sudo nano /etc/systemd/system/medcabinet.service

	
2. Вставить (пути и юзер свои):
	```bash
	[Unit]
	Description=MedCabinet FastAPI application
	After=network.target

	[Service]
	User=user
	WorkingDirectory=/home/user/medcabinet
	ExecStart=/home/user/medcabinet/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8040
	Environment="PATH=/home/user/medcabinet/venv/bin"
	Restart=always

	[Install]
	WantedBy=multi-user.target
	
3. Сохранить и выйти.

4. Активировать службу:
	```bash
	sudo systemctl daemon-reload
	sudo systemctl enable medcabinet.service
	sudo systemctl start medcabinet.service


