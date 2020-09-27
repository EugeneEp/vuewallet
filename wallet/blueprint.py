from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from sqlalchemy import and_
from flask_login import current_user
import jwt
from app import db
from models import Users, Transactions, Wallets, hashpass, hashcsv, mergeTwoListsAsDict, Sms_approve, API, timeToDate, dateToTime, movementTranslate, getUserByToken, paginatorParse, transParse
import requests
import time as timec
import glob
import os
import re
import csv
import json
from app import token_required

wallet = Blueprint('wallet', __name__, template_folder = 'templates')

# Все транзакции
@wallet.route('/transactions/back', methods=['POST'])
@token_required
def index(self):
	data = request.get_json()
	page = int(data.get('page', 1))

	date_from = data.get('from')
	date_end = data.get('to')
	filters = []

	if date_from and date_from != "":
		filters.append(Transactions.time > dateToTime(date_from))
	if date_end and date_end != "":
		filters.append(Transactions.time < dateToTime(date_end))

	user = getUserByToken(request.headers.get('Authorization'))
	transactions = user.transactions.filter(and_(*filters)).order_by(Transactions.id.desc()).paginate(page=page, per_page=8)

	t = transParse(transactions.items)
	p = paginatorParse(transactions)
	return json.dumps({'success':True,'msg':'','trans':t,'paginator':p})

# Профиль
@wallet.route('/profile/back', methods=['GET', 'POST'])
@token_required
def profile(self):
	if request.method == 'GET':
		identity = {'fullname': '', 'passport': '', 'passportIssuedAt': ''}
		user = getUserByToken(request.headers.get('Authorization'))
		if user.identity:
			identity.update(json.loads(user.identity))
		return json.dumps({'success':True,'msg':'', 'identity':identity})
	else:

		data = request.get_json()
		fullname = data.get('fullname')
		passport = data.get('passport')
		passportIssuedAt = data.get('passportIssuedAt')

		if fullname == '' and passport == '' and passportIssuedAt == '':
			return json.dumps({'success':False,'msg':'Не все поля заполнены'})
		
		fullnameArr = fullname.split()
		passport = passport.replace(' ', '')

		if len(fullnameArr) < 3:
			return json.dumps({'success':False,'msg':'ФИО введены не корректно'})

		identity = {
			'fullname': fullname,
			'lastName': fullnameArr[0],
			'firstName': fullnameArr[1],
			'secondName': fullnameArr[2],
			'passport': passport,
			'passportIssuedAt':passportIssuedAt
		}

		identity = json.dumps(identity)

		user = getUserByToken(request.headers.get('Authorization'))
		user.identity = identity

		db.session.add(user)
		db.session.commit()

		return json.dumps({'success':True,'msg':'Данные успешно отправлены'})

# Загрузить аватарку
@wallet.route('/profile_picture/back', methods=['POST'])
@token_required
def profile_picture(self):
	if request.method == 'POST':
		if request.files['img']:
			user = getUserByToken(request.headers.get('Authorization'))
			for x in glob.glob('static/upload/profile/' + str(user.id) + '.png'):
				os.unlink(x)
			f = request.files['img']
			ext = f.filename.split('.')[1]
			f.filename = str(user.id) + '.png'
			
			try:
				f.save('static/upload/profile/' + f.filename)
			except:
				return json.dumps({'success':False,'msg':'Что-то пошло не так'})

			return json.dumps({'success':True,'msg':'Фотография обновлена'})
		else:
			return json.dumps({'success':False,'msg':'Файл не найден'})
	else:
		return json.dumps({'success':False,'msg':'Метод не найден'})

# Пополнить кошелек
@wallet.route('/charge/back', methods=['GET', 'POST'])
@token_required
def charge(self):
	if request.method == 'GET':
		return render_template('wallet/charge.html')
	else:
		return json.dumps({'success':False,'msg':'Метод еще не готов'})

# Перевод
@wallet.route('/transfer/back', methods=['GET', 'POST'])
@token_required
def transfer(self):
	if request.method == 'GET':
		return render_template('wallet/transfer.html')
	else:
		return json.dumps({'success':False,'msg':'Метод еще не готов'})

# Создать ссылку для сбора средств на 
@wallet.route('/moneybank/back', methods=['GET', 'POST'])
@token_required
def moneybank(self):
	if request.method == 'GET':
		return render_template('wallet/moneybank.html')
	else:
		return json.dumps({'success':False,'msg':'Метод еще не готов'})

# Создать ссылку на пожертвования
@wallet.route('/donate/back', methods=['GET', 'POST'])
@token_required
def donate(self):
	if request.method == 'GET':
		return render_template('wallet/donate.html')
	else:
		return json.dumps({'success':False,'msg':'Метод еще не готов'})

@wallet.route('/partner')
@token_required
def partner(self):
	return render_template('wallet/partner.html')

@wallet.route('/csv/back', methods=['POST'])
@token_required
def csv_transactions(self):
	if request.method == 'POST':
		data = request.get_json()
		try:

			mylist = [['Дата', 'Тип транзакции', 'Статус', 'Сумма']]

			date_from = data.get('from')
			date_end = data.get('to')
			filters = []

			if date_from and date_from != "":
				filters.append(Transactions.time > dateToTime(date_from))
			if date_end and date_end != "":
				filters.append(Transactions.time < dateToTime(date_end))
			

			user = getUserByToken(request.headers.get('Authorization'))
			transactions = user.transactions.filter(and_(*filters)).order_by(Transactions.id.desc()).all()

			for t in transactions:
				t.time = timeToDate(t.time)
				t.movement_type = movementTranslate(t.movement_type)
				mylist.append([t.time, t.movement_type, t.status, t.amount])

			
			link = hashcsv(user.id)

			with open(link, 'w', newline='', encoding='cp1251') as myfile:
				wr = csv.writer(myfile, delimiter=";")
				for x in mylist:
					wr.writerow(x)

			return json.dumps({'success':True, 'msg':'', 'link': request.host_url + link + '?t=' + str(timec.time())})

		except:
			return json.dumps({'success':False,'msg':'Что-то пошло не так'})
	else:
		return json.dumps({'success':False,'msg':'Метод не найден'})

