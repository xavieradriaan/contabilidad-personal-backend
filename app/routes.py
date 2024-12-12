# routes.py
from flask import request, jsonify, make_response
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers import IngresoController, OtroIngresoController, EgresoController, PagoRecurrenteController, TotalController
from app import app, db, api, bcrypt
from app.models import User, Ingreso, OtroIngreso, Egreso, PagoRecurrente
from flask_jwt_extended import create_access_token
from mailjet_rest import Client
import random
import os
from datetime import datetime, timedelta
from calendar import month_name
from babel.dates import get_month_names


# Configurar la clave API de Mailjet
MAILJET_API_KEY = "ba07f36f2dd4c3aa5a89811f3ca3a54e"
MAILJET_API_SECRET = "6aa94d9f4a1f095e0a2e02f29a7bf935"

mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')

def send_otp(email, username):
    otp = random.randint(100000, 999999)
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "contabilizateapp@hotmail.com",  # Asegúrate de que esta dirección esté verificada en Mailjet
                    "Name": "Contabilízate App"
                },
                "To": [
                    {
                        "Email": email,
                        "Name": username
                    }
                ],
                "Subject": "Código de Confirmación",
                "HTMLPart": f"""
                <p>Hola {username},</p>
                <p>Bienvenido a la aplicación de Contabilízate App, tu aplicación para llevar tu contabilidad personal.</p>
                <p>Tu código de confirmación es: <strong>{otp}</strong></p>
                <p>Su usuario es: <strong>{username}</strong></p>
                """
            }
        ]
    }
    result = mailjet.send.create(data=data)
    if result.status_code != 200:
        app.logger.error(f"Error sending email: {result.json()}")
        raise Exception("Error sending email")
    return otp

@app.route('/')
def index():
    return "Bienvenido a la API de Contabilidad Personal"

@app.route('/check_username', methods=['GET'])
def check_username():
    username = request.args.get('username')
    if not username:
        return jsonify({'available': False, 'message': 'Username is required'}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({'available': False, 'message': 'El nombre de usuario ya está en uso'}), 200
    else:
        return jsonify({'available': True, 'message': 'El nombre de usuario está disponible'}), 200

@app.route('/check_email', methods=['GET'])
def check_email():
    email = request.args.get('email')
    if not email:
        return jsonify({'exists': False, 'message': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'exists': True, 'message': 'El correo existe'}), 200
    else:
        return jsonify({'exists': False, 'message': 'El correo no se encuentra registrado'}), 404

class RegisterResource(Resource):
    def post(self):
        data = request.get_json()
        username = data['username']
        email = data['email']
        password = data['password']

        if ' ' in username or ' ' in password:
            return make_response(jsonify({"message": "El nombre de usuario y la contraseña no deben contener espacios."}), 400)

        user = User.query.filter_by(username=username).first()
        if user:
            return make_response(jsonify({"message": "El nombre de usuario ya existe o está en uso. Por favor use otro Nombre de Usuario"}), 400)
        
        user = User.query.filter_by(email=email).first()
        if user:
            return make_response(jsonify({"message": "El correo electrónico ya está en uso. Por favor use otro correo electrónico"}), 400)

        otp = send_otp(email, username)
        otp_expiration = datetime.utcnow() + timedelta(minutes=5)

        new_user = User(username=username, email=email, password=password, otp=str(otp), otp_expiration=otp_expiration)
        db.session.add(new_user)
        db.session.commit()

        return make_response(jsonify({"message": "Código de confirmación enviado al correo electrónico. Por favor, ingrese el código enviado a su bandeja Principal o su Buzón no deseado para completar el registro."}), 201)
class ConfirmOTPResource(Resource):
    def post(self):
        data = request.get_json()
        email = data['email']
        otp = data['otp']

        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({"message": "El correo electrónico no está registrado."}), 404)

        if user.otp != otp or user.otp_expiration < datetime.utcnow():
            return make_response(jsonify({"message": "Código de confirmación inválido o expirado."}), 400)

        hashed_password = bcrypt.generate_password_hash(user.password).decode('utf-8')
        user.password = hashed_password
        user.otp = None
        user.otp_expiration = None
        db.session.commit()

        return make_response(jsonify({"message": "Registro completado exitosamente."}), 200)

api.add_resource(RegisterResource, '/register')
api.add_resource(ConfirmOTPResource, '/confirm_otp')

class PasswordResetRequestResource(Resource):
    def post(self):
        data = request.get_json()
        email = data['email']

        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({"message": "El correo electrónico no está registrado."}), 404)

        otp = send_otp(email, user.username)
        user.otp = str(otp)
        user.otp_expiration = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()

        return make_response(jsonify({"message": "Código de recuperación enviado al correo electrónico."}), 200)

class PasswordResetResource(Resource):
    def post(self):
        data = request.get_json()
        email = data['email']
        otp = data['otp']
        new_password = data['new_password']

        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({"message": "El correo electrónico no está registrado."}), 404)

        if user.otp != otp or user.otp_expiration < datetime.utcnow():
            return make_response(jsonify({"message": "Código de confirmación inválido o expirado."}), 400)

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password = hashed_password
        user.otp = None
        user.otp_expiration = None
        db.session.commit()

        return make_response(jsonify({"message": "Contraseña actualizada correctamente."}), 200)

api.add_resource(PasswordResetRequestResource, '/password_reset_request')
api.add_resource(PasswordResetResource, '/password_reset')

class IngresoResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        ingresos = IngresoController.get_all_ingresos(user.id)
        return jsonify([ingreso.to_dict() for ingreso in ingresos])

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        data = request.get_json()
        descripcion = data.get('descripcion', '')
        
        if data['fuente'] == 'Ingresos Extras':
            nuevo_otro_ingreso = OtroIngresoController.create_otro_ingreso(data['fuente'], data['fecha'], data['monto'], user.id, descripcion)
            return jsonify(nuevo_otro_ingreso.to_dict())
        else:
            if data['fuente'] == 'Ingresar Salario (Quincena)':
                descripcion = 'Quincena'
            elif data['fuente'] == 'Ingresar Salario (Fin de Mes)':
                descripcion = 'Fin de Mes'
            nuevo_ingreso = IngresoController.create_ingreso(data['fuente'], data['fecha'], data['monto'], user.id, descripcion)
            return jsonify(nuevo_ingreso.to_dict())

api.add_resource(IngresoResource, '/ingresos')

class OtroIngresoResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        otros_ingresos = OtroIngresoController.get_all_otros_ingresos(user.id)
        return jsonify([otro_ingreso.to_dict() for otro_ingreso in otros_ingresos])

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        data = request.get_json()
        nuevo_otro_ingreso = OtroIngresoController.create_otro_ingreso(
            fuente=data['fuente'],
            fecha=data['fecha'],
            monto=data['monto'],
            user_id=user.id,
            descripcion=data.get('descripcion', '')
        )
        return jsonify(nuevo_otro_ingreso.to_dict())

api.add_resource(OtroIngresoResource, '/otros_ingresos')

class EgresoResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        egresos = EgresoController.get_all_egresos(user.id)
        return jsonify([egreso.to_dict() for egreso in egresos])

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        data = request.get_json()
        nuevo_egreso = EgresoController.create_egreso(
            categoria=data['categoria'],
            subcategoria=data.get('subcategoria', ''),
            monto=data['monto'],
            fecha=data['fecha'],
            user_id=user.id,
            bancos=data.get('bancos', None),  # Pasar el banco al controlador
            recurrente=data.get('recurrente', False)
        )
        return jsonify(nuevo_egreso.to_dict())

api.add_resource(EgresoResource, '/egresos')

class CheckEgresosResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        egresos = EgresoController.get_all_egresos(user.id)
        return jsonify({"egresos_registrados": len(egresos) > 0})

api.add_resource(CheckEgresosResource, '/check_egresos')

class TotalResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        
        year = request.args.get('year')
        month = request.args.get('month')
        
        if not year or not month:
            return make_response(jsonify({"message": "Year and month are required"}), 400)
        
        year = int(year)
        month = int(month)
        
        ingresos = Ingreso.query.filter_by(user_id=user.id).filter(db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).all()
        otros_ingresos = OtroIngreso.query.filter_by(user_id=user.id).filter(db.extract('year', OtroIngreso.fecha) == year, db.extract('month', OtroIngreso.fecha) == month).all()
        egresos = Egreso.query.filter_by(user_id=user.id).filter(db.extract('year', Egreso.fecha) == year, db.extract('month', Egreso.fecha) == month).all()
        
        total_ingresos = sum([ingreso.monto for ingreso in ingresos])
        total_otros_ingresos = sum([otro_ingreso.monto for otro_ingreso in otros_ingresos])
        total_egresos = sum([egreso.monto for egreso in egresos])
        total = total_ingresos + total_otros_ingresos - total_egresos
        
        saldo_anterior, saldo_disponible = TotalController.get_saldo_disponible(user.id, year, month)
        month_names = get_month_names(locale='es')
        nombre_mes = month_names[month].capitalize()  # Capitalizar la primera letra
        
        return jsonify({
            "total_ingresos": float(total_ingresos),
            "total_otros_ingresos": float(total_otros_ingresos),
            "total_egresos": float(total_egresos),
            "total": float(total),
            "saldo_anterior": float(saldo_anterior),
            "saldo_disponible": float(saldo_disponible),
            "nombre_mes": nombre_mes,
            "detalles_ingresos": [ingreso.to_dict() for ingreso in ingresos],
            "detalles_otros_ingresos": [otro_ingreso.to_dict() for otro_ingreso in otros_ingresos],
            "detalles_egresos": [egreso.to_dict() for egreso in egresos]
        })

api.add_resource(TotalResource, '/total')

class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        if not user:
            return make_response(jsonify({"message": "Usuario no existe"}), 404)

        if user.failed_attempts >= 3:
            return make_response(jsonify({"message": "El usuario se ha bloqueado. Por favor, comunícate con tu administrador"}), 403)

        if user and bcrypt.check_password_hash(user.password, data['password']):
            user.failed_attempts = 0  # Reset failed attempts on successful login
            db.session.commit()
            access_token = create_access_token(identity=user.username)
            return jsonify(access_token=access_token)
        else:
            user.failed_attempts += 1
            db.session.commit()
            remaining_attempts = 3 - user.failed_attempts
            return make_response(jsonify({"message": f"Credenciales incorrectas. Intentos restantes: {remaining_attempts}", "remaining_attempts": remaining_attempts}), 401)

api.add_resource(LoginResource, '/login')

class UsersResource(Resource):
    def get(self):
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])

api.add_resource(UsersResource, '/users')

class PagoRecurrenteResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        
        year = request.args.get('year')
        month = request.args.get('month')
        
        if not year or not month:
            return make_response(jsonify({"message": "Year and month are required"}), 400)
        
        year = int(year)
        month = int(month)
        
        pagos_recurrentes = PagoRecurrenteController.get_pagos_recurrentes(user.id, year, month)
        return jsonify(pagos_recurrentes)

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        data = request.get_json()
        categorias = data.get('categorias', [])
        PagoRecurrenteController.save_pagos_recurrentes(user.id, categorias)
        return jsonify({"message": "Pagos recurrentes actualizados"})

api.add_resource(PagoRecurrenteResource, '/pagos_recurrentes')

class DepositosBancosResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        
        year = request.args.get('year')
        month = request.args.get('month')
        
        if year and month:
            egresos = Egreso.query.filter_by(user_id=user.id).filter(db.extract('year', Egreso.fecha) == year, db.extract('month', Egreso.fecha) == month).all()
        else:
            egresos = Egreso.query.filter_by(user_id=user.id).all()
        
        depositos_por_banco = {}
        total_depositos = 0

        for egreso in egresos:
            if (banco := egreso.bancos):
                if banco not in depositos_por_banco:
                    depositos_por_banco[banco] = []
                depositos_por_banco[banco].append({
                    'fecha': egreso.fecha.isoformat(),
                    'categoria': egreso.categoria,
                    'monto': float(egreso.monto)
                })
                total_depositos += float(egreso.monto)

        return jsonify({
            "depositosPorBanco": depositos_por_banco,
            "totalDepositos": total_depositos
        })

api.add_resource(DepositosBancosResource, '/depositos_bancos')

class CheckIngresosResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        
        # Recepción de parámetros year y month desde la URL
        year = request.args.get('year')
        month = request.args.get('month')
        
        # Validación de que los parámetros year y month están presentes
        if not year or not month:
            return make_response(jsonify({"message": "Year and month are required"}), 400)
        
        # Conversión de los parámetros year y month a enteros
        year = int(year)
        month = int(month)
        
        # Consulta en la base de datos para verificar si existen ingresos de Quincena y Fin de Mes
        quincena_exists = Ingreso.query.filter_by(user_id=user.id, descripcion='Quincena').filter(db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).first() is not None
        fin_mes_exists = Ingreso.query.filter_by(user_id=user.id, descripcion='Fin de Mes').filter(db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).first() is not None
        
        # Respuesta del endpoint
        return jsonify({
            "quincena_exists": quincena_exists,
            "fin_mes_exists": fin_mes_exists
        })

# Registro del recurso en la API
api.add_resource(CheckIngresosResource, '/check_ingresos')
@app.route("/test_email")
def test_email():
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "tu_correo_verificado@ejemplo.com",  # Asegúrate de que esta dirección esté verificada en Mailjet
                    "Name": "Tu Nombre"
                },
                "To": [
                    {
                        "Email": "xaviline6@live.com",
                        "Name": "Usuario"
                    }
                ],
                "Subject": "Hello World",
                "HTMLPart": "<strong>it works!</strong>"
            }
        ]
    }
    result = mailjet.send.create(data=data)
    return jsonify({"status": result.status_code, "body": result.json()})

if __name__ == "__main__":
    app.run()