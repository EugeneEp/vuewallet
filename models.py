from app import db
from datetime import datetime
from flask import current_app
import re
import hashlib
import glob
import os
import time as timec
import random
import requests
import json
import jwt

# Функция на замену пробелов на "-", в случае если придется генерировать урл с названием чего либо
def slugify(s):
	pattern = r'[^\w+]'
	return re.sub(pattern, '-', s)

# функция на замену значений типа транзакций, полученным по апи
def movementTranslate(m):
	arr = {'charge':'Пополнение','withdraw':'Вывод','payment':'Перевод'}
	return arr[m]

# Функция шифрования пароля в мд5
def hashpass(password):
	salt = '69hdaw@e21e2'
	new_pass = password + salt
	h = hashlib.md5(new_pass.encode())
	return h.hexdigest()

# Функция шифрования ссылки на csv файл транзакций
def hashcsv(user_id):
	salt = 'j12090d)()(@'
	link = str(user_id) + salt
	h = hashlib.md5(link.encode())
	return 'static/upload/csv/' + h.hexdigest() + '.csv'

# Функция шифрования файла фото профиля
def hashprofile(user_id):
	salt = 'pp12oj321jp)('
	link = str(user_id) + salt
	h = hashlib.md5(link.encode())
	return h.hexdigest()

# Функция на слияние двух списков в нужный мне формат (не используется)
def mergeTwoListsAsDict(list1, list2):
	dict1 = {k: {'name': v} for k, v in enumerate(list1)}
	dict2 = {k: {'id': v} for k, v in enumerate(list2)}
	return {k: {**v, **dict2[k]} for k, v in dict1.items()}

# Функция конвертации таймстампа в дату
def timeToDate(time):
	timestamp = datetime.fromtimestamp(time)
	return timestamp.strftime('%Y-%m-%d %H:%M:%S')

# Функция ковертации даты в таймстамп
def dateToTime(time):
	return timec.mktime(datetime.strptime(time, "%Y-%m-%d").timetuple())

# Получить юзера по данным токена
def getUserByToken(header):
	auth_headers = header.split()
	if len(auth_headers) != 2:
		return None
	token = auth_headers[1]
	data = jwt.decode(token, current_app.config['SECRET_KEY'])
	user = Users.query.filter(Users.phone==data['sub']).first()
	return user

# Конвертация объекта пагинатора в словарь
def paginatorParse(obj):
	arr = {
		'pages':obj.pages,
		'page':obj.page,
		'has_prev':obj.has_prev,
		'prev_num':obj.prev_num,
		'has_next':obj.has_next,
		'next_num':obj.next_num
	}
	return arr

# Конвертация объекта транзакций в словарь
def transParse(obj):
	arr = {}
	for v in obj:
		v.time = timeToDate(v.time)
		v.movement_type = movementTranslate(v.movement_type)
		arr[v.id] = {
			'time': v.time,
			'movement_type': v.movement_type,
			'amount': v.amount,
			'status': v.status 
		}
	return arr

# Класс для работы с апи
class API():
	url = 'https://apis-dev.maxwallet.ru/' # Урл апи
	api_key = '????????' # Апи ключ
	headers = {"Content-Type" : "application/json", "X-API-KEY" : api_key} # Заголовки

	# Конструктор, в который передаю название метода для исполнения
	def __init__(self, method, body):
		self.method = method
		self.url = self.url + self.method
		self.body = body


	# Метод для гет запроса
	def get(self):
		response = requests.get(self.url, headers=self.headers, params=self.body)
		return response.json()

	# Метод для пост запроса
	def post(self):
		response = requests.post(self.url, headers=self.headers, json=self.body)
		return response.json()

# Класс пользователей
class Users(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(255), nullable=True)
	phone = db.Column(db.BigInteger, nullable=True)
	password = db.Column(db.String(255))
	identity = db.Column(db.Text, nullable=True)
	confirmation = db.Column(db.String(255), default = 0)
	roots = db.Column(db.Integer, default = 1)
	secret_id = db.Column(db.Text, nullable=True)
	secret_key = db.Column(db.Text, nullable=True)
	self_employed_approve = db.Column(db.Integer, nullable=True)
	rate = db.Column(db.Float, nullable=True)
	balance = 0

	# Связь 1 ко многим, для получение кошельков юзера
	wallets = db.relationship("Wallets", backref=db.backref('user'), lazy='dynamic')

	# Связь 1 ко многим, для получение транзакций юзера
	transactions = db.relationship("Transactions", backref=db.backref('user'), lazy='dynamic')

	def __init__(self, *args, **kwargs):
		super(Users, self).__init__(*args, **kwargs)
		self.generate_hash()

	# Зашифровать пароль
	def generate_hash(self):
		self.password = hashpass(self.password)

	# Добавить юзера по апи в банк
	def add_user(self):
		body = {
			'phone' : self.phone
		}
		method = 'customMethods/users'
		response = API(method=method, body=body).post()
		if response['ok'] == True :
			self.secret_id = response['data']['id']
		return response

	# Передать параметры идентификации юзера по апи в банк
	def add_identity(self, data):
		body = {k: v for k, v in data.items() if v != ''}
		method = 'customMethods/users/' + self.secret_id + '/identity'
		response = API(method=method, body=body).post()
		return response

	# Получить информацию о прохождении идентификации юзера
	def get_identity(self):
		method = 'customMethods/users/' + self.secret_id + '/identity'
		response = API(method=method, body={}).get()
		return response


# Класс кошельков юзера
class Wallets(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	wallet_id = db.Column(db.String(255), nullable=True)
	amount = db.Column(db.String(255), default=0)
	status = db.Column(db.Integer)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	comment = db.Column(db.String(192), nullable=True)
	secret_id = db.Column(db.String(255), nullable=True)
	deleted = db.Column(db.Integer)

	def __init__(self, *args, **kwargs):
		super(Wallets, self).__init__(*args, **kwargs)

# Класс транзакций юзера
class Transactions(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	wallet_sender_id = db.Column(db.Integer, nullable=True)
	wallet_reciever_id = db.Column(db.Integer, nullable=True)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	movement_type = db.Column(db.String(255))
	amount = db.Column(db.String(255))
	commission = db.Column(db.String(255))
	time = db.Column(db.Integer, default=timec.time())
	secret_t = db.Column(db.String(255), nullable=True)
	status = db.Column(db.Integer, default=1)
	card = db.Column(db.String(255), nullable=True)
	email = db.Column(db.String(255), nullable=True)
	link = db.Column(db.Integer, nullable=True)

	def __init__(self, *args, **kwargs):
		super(Transactions, self).__init__(*args, **kwargs)

# Класс для работы с смс
class Sms_approve(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, nullable=True)
	code = db.Column(db.Integer)
	action = db.Column(db.String(255))
	time = db.Column(db.Integer, default=timec.time())
	status = db.Column(db.Integer, default=0)
	phone = db.Column(db.String(255))
	api_url = 'https://api.smsgold.ru' # Урл апи смс сервиса
	method_getToken = '????????????' # Токен
	method_send = '/sms/v1/message/sendOne' # Метод для отправки смс

	def __init__(self, *args, **kwargs):
		super(Sms_approve, self).__init__(*args, **kwargs)
		self.generate_code()

	# Сгенерировать код
	def generate_code(self):
		self.code = 1111
		#self.code = random.randint(1000,9999)

	# Обновить время отправления смс, при повторной отправке
	def update_time(self):
		self.time = timec.time()

	# Метод для отправки смс
	def send_sms(self):
		headers = {"Content-Type" : "application/json", "charset" : "utf-8", "X-SDK" : "python | 0.0.1"}
		url = self.api_url + self.method_getToken
		response = requests.get(url, headers=headers)
		response = response.json()
		accessToken = response['accessToken']
		
		body = {
			'channel' : 'sms',
			'sms_text' : self.code,
			'viber_text' : '',
			'sms_sender' : 'SmsGold',
			'viber_sender' : '',
			'phone' : self.phone
		}

		headers['Authorization'] = 'Bearer ' + accessToken
		url = self.api_url + self.method_send

		response = requests.post(url, headers=headers, json=body)
		response = response.json()
		return response