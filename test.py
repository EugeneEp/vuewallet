from app import app
from app import client
import view
import json
import pytest
from wallet.blueprint import wallet

app.register_blueprint(wallet, url_prefix='/wallet')

def pytest_namespace():
	return {'user':{}}

@pytest.fixture
def data():
	arr = {
		'phone':'71111111112',
		'password':'11111111'
	}
	res = client.post('/login', json=arr)
	res_json = json.loads(res.data)
	pytest.user = res_json

def test_get(data):
	res = client.get('/')
	res_json = json.loads(res.data)

	assert res.status_code == 200
	assert res_json['success'] == True

def test_get_transactions(data):
	headers = {
		"Content-Type" : "application/json",
		"Authorization" : "Bearer: " + pytest.user['token']
	}
	arr = {

	}
	res = client.post('/wallet/transactions/back', json=arr, headers=headers)

	res_json = json.loads(res.data)

	assert res.status_code == 200
	assert res_json['success'] == True

def test_profile(data):
	headers = {
		'Content-Type':'application/json',
		'Authorization':'Bearer: ' + pytest.user['token']
	}
	res = client.get('/wallet/profile/back', headers=headers)

	res_json = json.loads(res.data)

	print(res_json)

	assert res.status_code == 200
	assert res_json['success'] == True