from flask import Flask
from flask import redirect
from flask import url_for
from flask import request
import json
from config import Configuration
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
import jwt
from functools import wraps
from flask import current_app

app = Flask(__name__)
app.config.from_object(Configuration)
db = SQLAlchemy(app)
client = app.test_client()


#enable CORS
CORS(app)

from models import Users
login_manager = LoginManager(app)

def token_required(f):
	@wraps(f)
	def _verify(*args, **kwargs):
		auth_headers = request.headers.get('Authorization', '').split()

		invalid_msg = {'success':False, 'msg': 'Неверный токен'}
		expired_msg = {'success':False, 'msg': 'Нужно авторизоваться'}
		if len(auth_headers) != 2:
			return json.dumps(invalid_msg)
		if auth_headers[0] != 'Bearer':
			return json.dumps(invalid_msg)
		try:
			token = auth_headers[1]
			data = jwt.decode(token, current_app.config['SECRET_KEY'])
			user = Users.query.filter(Users.phone==data['sub']).first()
			if not user:
				raise RuntimeError('User not found')
			return f(user, *args, **kwargs)
		except jwt.ExpiredSignatureError:
			return json.dumps(expired_msg)
		except (jwt.InvalidTokenError, Exception) as e:
			print('test')
			print(e)
			return json.dumps(invalid_msg)

	return _verify