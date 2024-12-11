#__init__.py
import atexit
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_login import LoginManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from apscheduler.schedulers.background import BackgroundScheduler
from flask_migrate import Migrate
import os
from datetime import timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://xavier:1234@localhost/contabilidad_personal'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=40)  # Expiración del token en 5 minutos

db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app)
login_manager = LoginManager(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)  # Habilitar CORS para todas las rutas

from app import routes
from app.models import PagoRecurrente  # Importar el modelo PagoRecurrente
from app.controllers import PagoRecurrenteController  # Importar el controlador PagoRecurrenteController

def reset_pagos_recurrentes():
    with app.app_context():
        PagoRecurrenteController.reset_pagos_recurrentes()
        app.logger.info("Pagos recurrentes restablecidos")

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=reset_pagos_recurrentes,
    trigger='cron',
    day='last',
    hour=23,
    minute=59,
    second=59
)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))