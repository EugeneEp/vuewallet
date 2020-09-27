from app import app
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import current_app
from app import db
from models import Users, hashpass, mergeTwoListsAsDict, Sms_approve, API, getUserByToken
import requests
import time
from datetime import datetime, timedelta
import re
import json
import jwt

# index
#@app.route('/')
#def index():
	#return render_template('index.html')

# Роут на страницы с информацией о компании
#@app.route('/<template>/info')
#def info(template):
#	reqired_templates = ['start-business', 'about', 'business', 'capabilities', 'contacts', 'events', 'gaming', 'stream']
#	if template not in reqired_templates:
#		return render_template( 'index.html' )
#	return render_template( template + '.html' )

# Регистрация
@app.route('/registration', methods=['POST'])
def reg_user():
	if request.method == 'POST':
		data = request.get_json()
		phone = data.get('phone')
		phone = re.sub("\D", "", phone)
		password = data.get('password')
		confirm = data.get('confirm')

		user = Users.query.filter(Users.phone==phone).first()
		sms = Sms_approve.query.filter(Sms_approve.phone == phone, Sms_approve.action == 'reg').first()
		if sms:
			if sms.status == 0:
				return json.dumps({'success':False,'msg':'Вы не подтвердили смс'})
			if user and sms.status == 1:
				return json.dumps({'success':False,'msg':'Такой пользователь уже зарегистрирован'})
		else:
			return json.dumps({'success':False,'msg':'Вы не отправили смс'})

		if phone == '' or password == '' or confirm == '':
			return json.dumps({'success':False,'msg':'Не все поля заполнены'})
		if confirm != password:
			return json.dumps({'success':False,'msg':'Пароли не совпадают'})
		user = Users(phone=phone, password=password)

		# Добавить юзера в банк по апи
		#add_user = user.add_user()
		#if add_user['ok'] != True:
		#	return json.dumps({'success':False,'msg':'Не получилось добавить в систему'})

		db.session.add(user)
		db.session.flush()
		db.session.commit()
		token = jwt.encode({
			'sub': user.phone,
			'iat':datetime.utcnow(),
			'exp': datetime.utcnow() + timedelta(days=3)},
			current_app.config['SECRET_KEY'])

	return json.dumps({'success':True,'msg':'Успех','token': token.decode('UTF-8'), 'id': user.id})

# Вход
@app.route('/login', methods=['POST'])
def log_user():
	if request.method == 'POST':
		data = request.get_json()
		phone = data.get('phone')
		phone = re.sub("\D", "", phone)
		password = data.get('password')
		if phone == '' or password == '':
			return json.dumps({'success':False,'msg':'Не все поля заполнены'})
		user = Users.query.filter(Users.phone==phone, Users.password==hashpass(password)).first()
		if user:
			if user.roots == 0:
				return json.dumps({'success':False,'msg':'Вы не прошли подтверждение'})
			
			token = jwt.encode({
			'sub': user.phone,
			'iat':datetime.utcnow(),
			'exp': datetime.utcnow() + timedelta(days=3)},
			current_app.config['SECRET_KEY'])

			return json.dumps({'success':True,'msg':'','token': token.decode('UTF-8'), 'id': user.id})
		else:
			return json.dumps({'success':False,'msg':'Телефон и пароль не совпадают'})
	else:
		return json.dumps({'success':False,'msg':'Request method error'})

# Выход
#@app.route('/logout')
#@login_required
#def logout():
#	logout_user()
#	return json.dumps({'success':True,'msg':''})

# Отправить код по смс
@app.route('/sms', methods=['POST'])
def sms():
	if request.method == 'POST':
		data = request.get_json()
		timelimit = int(time.time())
		phone = data.get('phone')
		sms_type = data.get('type')

		phone = re.sub("\D", "", phone)

		if len(str(phone)) < 11:
			return json.dumps({'success':False,'msg':'Телефон введен не верно'})

		re_sms = Sms_approve.query.filter(Sms_approve.phone==phone, Sms_approve.action==sms_type).first()

		# Было ли отправлено смс по этому номеру, на конкретное действие
		if re_sms:
			if (timelimit - re_sms.time) < 60:
				return json.dumps({'success':False,'msg':'Повторное смс будет доступно через 60 секунд'})
			elif re_sms.action == 'reg' and re_sms.status == 1:
				return json.dumps({'success':False,'msg':'Такой пользователь уже зарегистрирован'}) # Если код уже использован и подтвержден
			else:
				re_sms.generate_code()
				re_sms.update_time()
				re_sms.status = 0
				# Отправить повторное смс по апи
				#send = re_sms.send_sms()
				db.session.commit()
		else:
			if request.headers.get('Authorization'):
				user = getUserByToken(request.headers.get('Authorization'))
				if user:
					sms = Sms_approve(user_id=user.id, action=sms_type, phone=phone)
			else:
				sms = Sms_approve(action=sms_type, phone=phone)

			# Отправить смс по апи
			#send = sms.send_sms()
			db.session.add(sms)
			db.session.commit()

	else:
		return json.dumps({'success':False,'msg':'Request method error'})

	return json.dumps({'success':True,'msg':'Успех'})

# Проверка кода смс
@app.route('/sms_check', methods=['POST'])
def sms_check():
	if request.method == 'POST':
		data = request.get_json()
		phone = data.get('phone')
		phone = re.sub("\D", "", phone)
		sms_type = data.get('type')
		code = data.get('code')
		timelimit = int(time.time())

		sms = Sms_approve.query.filter(Sms_approve.status==0, Sms_approve.phone==phone, Sms_approve.action==sms_type, Sms_approve.code==code).first()

		if sms:
			if (timelimit - sms.time) > (60 * 60):
				return json.dumps({'success':False,'msg':'Проверочный код истек, отправьте повторное смс'})
			sms.status = 1
			db.session.commit()
		else:
			return json.dumps({'success':False,'msg':'Код смс введен не верно'})

	else:
		return json.dumps({'success':False,'msg':'Request method error'})

	return json.dumps({'success':True,'msg':'Успех'})