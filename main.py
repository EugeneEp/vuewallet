#!C:\python 3.8.1\python.exe

from app import app
from app import db
from wallet.blueprint import wallet

import view


app.register_blueprint(wallet, url_prefix='/wallet')

if __name__ == '__main__':
	app.run(port=1337, debug=True)