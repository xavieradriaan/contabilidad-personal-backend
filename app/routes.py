# routes.py
from flask import request, jsonify, make_response, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers import IngresoController, OtroIngresoController, EgresoController, PagoRecurrenteController, TotalController, CredencialController
from app import app, db, api, bcrypt
from app.models import User, Ingreso, OtroIngreso, Egreso, PagoRecurrente, Credencial
from flask_jwt_extended import create_access_token
from mailjet_rest import Client
import random
import os
from datetime import datetime, timedelta
from calendar import month_name
from babel.dates import get_month_names
from app.controllers import CredencialController
from app import app, api
from app.controllers import TarjetaCreditoController
from decimal import Decimal  # Importar Decimal para manejar valores monetarios
from flask_bcrypt import generate_password_hash
from functools import wraps

def validate_active_session(f):
    """
    Decorator para validar que la sesión actual sea la única activa
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return make_response(jsonify({
                "message": "Usuario no encontrado.",
                "session_expired": True
            }), 401)
        
        # Obtener el token actual del header Authorization
        auth_header = request.headers.get('Authorization', '')
        current_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # Verificar si el token actual coincide con el token de sesión activa
        if not user.active_session_token or user.active_session_token != current_token:
            return make_response(jsonify({
                "message": "Tu sesión ha sido cerrada debido a un nuevo inicio de sesión desde otro dispositivo.",
                "session_expired": True,
                "reason": "session_replaced"
            }), 401)
        
        return f(*args, **kwargs)
    return decorated_function

def credentials_session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
        if not user:
            return make_response(jsonify({"message": "Usuario no encontrado."}), 404)
        
        # Verificar si la sesión de credenciales es válida
        if (not user.credentials_session_valid_until or 
            user.credentials_session_valid_until < datetime.utcnow()):
            return make_response(jsonify({
                "message": "Acceso a credenciales requiere verificación.",
                "requires_otp": True
            }), 403)
        
        return f(*args, **kwargs)
    return decorated_function

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

def send_credentials_otp(email, username):
    otp = random.randint(100000, 999999)
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "contabilizateapp@hotmail.com",
                    "Name": "Contabilízate App"
                },
                "To": [
                    {
                        "Email": email,
                        "Name": username
                    }
                ],
                "Subject": "Código de Acceso a Credenciales",
                "HTMLPart": f"""
                <p>Hola {username},</p>
                <p>Has solicitado acceso a tus credenciales almacenadas en Contabilízate App.</p>
                <p>Tu código de verificación es: <strong>{otp}</strong></p>
                <p>Este código expira en 5 minutos por seguridad.</p>
                <p>Si no has solicitado este acceso, ignora este correo.</p>
                """
            }
        ]
    }
    result = mailjet.send.create(data=data)
    if result.status_code != 200:
        app.logger.error(f"Error sending credentials OTP email: {result.json()}")
        raise Exception("Error sending credentials OTP email")
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
        return jsonify({'exists': False, 'message': 'Email es requerido'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'exists': True, 'message': 'El correo ya está registrado'}), 200
    else:
        return jsonify({'exists': False, 'message': 'Correo disponible'}), 200
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

        hashed_password = generate_password_hash(password).decode('utf-8')
        otp = send_otp(email, username)
        otp_expiration = datetime.utcnow() + timedelta(minutes=5)

        new_user = User(username=username, email=email, password=hashed_password, otp=str(otp), otp_expiration=otp_expiration)
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

        # Quita el doble hasheo, solo limpia OTP
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
        user.failed_attempts = 0  # Reset failed attempts
        db.session.commit()

        return make_response(jsonify({"message": "Contraseña actualizada correctamente."}), 200)

api.add_resource(PasswordResetRequestResource, '/password_reset_request')
api.add_resource(PasswordResetResource, '/password_reset')

class IngresoResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        ingresos = IngresoController.get_all_ingresos(user.id)
        return jsonify([ingreso.to_dict() for ingreso in ingresos])

    @jwt_required()
    @validate_active_session
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
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
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        otros_ingresos = OtroIngresoController.get_all_otros_ingresos(user.id)
        return jsonify([otro_ingreso.to_dict() for otro_ingreso in otros_ingresos])

    @jwt_required()
    @validate_active_session
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
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
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        egresos = EgresoController.get_all_egresos(user.id)
        return jsonify([egreso.to_dict() for egreso in egresos])

    @jwt_required()
    @validate_active_session
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        data = request.get_json()

        # Validar campos requeridos
        required_fields = ['categoria', 'monto', 'fecha']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.error(f"Campo faltante: {field}")
                return {"message": f"El campo '{field}' es obligatorio."}, 400

        # Validar el campo 'tarjeta' solo si el tipo de egreso es 'credito'
        if data.get('tipo_egreso') == 'credito' and ('tarjeta' not in data or not data['tarjeta']):
            current_app.logger.error("Campo faltante: tarjeta")
            return {"message": "El campo 'tarjeta' es obligatorio para egresos de tipo 'credito'."}, 400

        try:
            tipo_egreso = data.get('tipo_egreso', 'debito')  # Default to 'debito'

            if tipo_egreso == 'credito':
                tarjeta_nombre = data['tarjeta']
                tarjeta = TarjetaCreditoController.get_tarjeta_by_nombre(tarjeta_nombre, user.id)
                if not tarjeta:
                    current_app.logger.error(f"Tarjeta no encontrada: {tarjeta_nombre}")
                    return {"message": "Tarjeta no encontrada"}, 404

                # Registrar consumo
                TarjetaCreditoController.registrar_consumo(tarjeta.id, data['monto'])

                # Crear egreso
                nuevo_egreso = EgresoController.create_egreso(
                    categoria=data['categoria'],
                    subcategoria=data.get('subcategoria', ''),
                    monto=Decimal(data['monto']),
                    fecha=data['fecha'],
                    user_id=user.id,
                    bancos=tarjeta.tarjeta_nombre,
                    tipo_egreso=tipo_egreso
                )
                return nuevo_egreso.to_dict(), 201
            else:
                # Crear egreso para tipo 'debito'
                nuevo_egreso = EgresoController.create_egreso(
                    categoria=data['categoria'],
                    subcategoria=data.get('subcategoria', ''),
                    monto=Decimal(data['monto']),
                    fecha=data['fecha'],
                    user_id=user.id,
                    bancos=data.get('bancos'),
                    tipo_egreso=tipo_egreso
                )
                return nuevo_egreso.to_dict(), 201
        except Exception as e:
            current_app.logger.error(f"Error en POST /egresos: {str(e)}")
            return {"message": "Error interno del servidor"}, 500

api.add_resource(EgresoResource, '/egresos')

class CheckEgresosResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        egresos = EgresoController.get_all_egresos(user.id)
        return jsonify({"egresos_registrados": len(egresos) > 0})

api.add_resource(CheckEgresosResource, '/check_egresos')

class TotalResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
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
        total_egresos = sum(e.monto for e in egresos if e.tipo_egreso != 'credito')
        total_tarjetas_credito = sum(e.monto for e in egresos if e.tipo_egreso == 'credito')
        total = total_ingresos + total_otros_ingresos - total_egresos
        
        saldo_anterior, saldo_disponible = TotalController.get_saldo_disponible(user.id, year, month)
        month_names = get_month_names(locale='es')
        nombre_mes = month_names[month].capitalize()  # Capitalizar la primera letra
        
        return jsonify({
            "total_ingresos": float(total_ingresos),
            "total_otros_ingresos": float(total_otros_ingresos),
            "total_egresos": float(total_egresos),
            "total_tarjetas_credito": float(total_tarjetas_credito),
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
            return make_response(jsonify({
                "message": "La cuenta se encuentra bloqueada. Se necesita restablecer la contraseña",
                "reset_url": "http://localhost:8080/password_reset"
            }), 403)  # Cambiar el mensaje y agregar URL

        if user and bcrypt.check_password_hash(user.password, data['password']):
            # Guardar información de la sesión anterior para notificación
            had_previous_session = user.active_session_token is not None
            previous_token = user.active_session_token
            
            # Crear nuevo token de acceso
            new_access_token = create_access_token(identity=user.id)
            
            # DEBUG: Log para verificar
            app.logger.info(f"Login - User: {user.username}")
            app.logger.info(f"Previous session existed: {had_previous_session}")
            app.logger.info(f"Previous token: {previous_token[:20] if previous_token else None}...")
            app.logger.info(f"New token: {new_access_token[:20]}...")
            
            # Actualizar información de sesión
            user.failed_attempts = 0
            user.active_session_token = new_access_token
            user.session_device_info = request.headers.get('User-Agent', 'Dispositivo desconocido')[:500]
            user.last_login_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'access_token': new_access_token,
                'session_replaced': had_previous_session,
                'message': 'Inicio de sesión exitoso' + (' - Sesión anterior cerrada' if had_previous_session else ''),
                'debug_info': {
                    'had_previous': had_previous_session,
                    'new_token_preview': new_access_token[:20] + '...'
                }
            })
        else:
            user.failed_attempts += 1
            db.session.commit()
            remaining_attempts = 3 - user.failed_attempts
            return make_response(jsonify({
                "message": f"Credenciales incorrectas. Intentos restantes: {remaining_attempts}",
                "remaining_attempts": remaining_attempts
            }), 401)

api.add_resource(LoginResource, '/login')

class UsersResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])

api.add_resource(UsersResource, '/users')

class PagoRecurrenteResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
        year = request.args.get('year')
        month = request.args.get('month')
        
        if not year or not month:
            return make_response(jsonify({"message": "Year and month are required"}), 400)
        
        year = int(year)
        month = int(month)
        
        pagos_recurrentes = PagoRecurrenteController.get_pagos_recurrentes(user.id, year, month)
        return jsonify(pagos_recurrentes)

    @jwt_required()
    @validate_active_session
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        data = request.get_json()
        categorias = data.get('categorias', [])
        PagoRecurrenteController.save_pagos_recurrentes(user.id, categorias)
        return jsonify({"message": "Pagos recurrentes actualizados"})

api.add_resource(PagoRecurrenteResource, '/pagos_recurrentes')

class DepositosBancosResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
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

class CredencialResource(Resource):
    @jwt_required()
    @credentials_session_required
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        credenciales = CredencialController.get_credenciales(user.id)
        return jsonify([credencial.to_dict() for credencial in credenciales])

    @jwt_required()
    @credentials_session_required
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        data = request.get_json()
        nueva_credencial = CredencialController.create_credencial(user.id, data['descripcion'], data['credencial'])
        return jsonify(nueva_credencial.to_dict())

    @jwt_required()
    @credentials_session_required
    def put(self):
        data = request.get_json()
        credencial_id = data.get('id')
        new_description = data.get('descripcion')
        new_credencial = data.get('credencial')

        # Validaciones básicas
        if not credencial_id or not new_description or not new_credencial:
            return {"message": "Todos los campos son obligatorios."}, 400

        # Obtener la credencial actual
        cred = Credencial.query.get(credencial_id)
        if not cred:
            return {"message": "Credencial no encontrada."}, 404

        # Verificar si hay cambios reales
        if cred.descripcion == new_description and cred.credencial == new_credencial:
            # SIEMPRE retorna el objeto credencial actual
            return {
                "message": "No se detectaron cambios.",
                "updated": False,
                "credencial": cred.to_dict()
            }, 200

        # Actualizar la credencial
        cred.descripcion = new_description
        cred.credencial = new_credencial
        db.session.commit()

        return {
            "message": "Credencial actualizada correctamente.",
            "updated": True,
            "credencial": cred.to_dict()
        }, 200

    @jwt_required()
    @credentials_session_required
    def delete(self):
        data = request.get_json()
        credencial = CredencialController.delete_credencial(data['id'])
        return jsonify(credencial.to_dict())

api.add_resource(CredencialResource, '/credenciales')

class CredentialsOTPRequestResource(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
        if not user:
            return make_response(jsonify({"message": "Usuario no encontrado."}), 404)
        
        try:
            otp = send_credentials_otp(user.email, user.username)
            user.credentials_otp = str(otp)
            user.credentials_otp_expiration = datetime.utcnow() + timedelta(minutes=5)
            db.session.commit()
            
            return make_response(jsonify({
                "message": "Código de verificación enviado a tu correo electrónico.",
                "success": True
            }), 200)
        except Exception as e:
            current_app.logger.error(f"Error sending credentials OTP: {str(e)}")
            return make_response(jsonify({
                "message": "Error al enviar el código de verificación.",
                "success": False
            }), 500)

class CredentialsOTPVerifyResource(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        data = request.get_json()
        otp = data.get('otp')
        
        if not user:
            return make_response(jsonify({"message": "Usuario no encontrado."}), 404)
        
        if not otp:
            return make_response(jsonify({"message": "Código OTP es requerido."}), 400)
        
        if (user.credentials_otp != otp or 
            not user.credentials_otp_expiration or 
            user.credentials_otp_expiration < datetime.utcnow()):
            return make_response(jsonify({
                "message": "Código de verificación inválido o expirado.",
                "success": False
            }), 400)
        
        # Limpiar el OTP y establecer sesión válida por 10 minutos
        user.credentials_otp = None
        user.credentials_otp_expiration = None
        user.credentials_session_valid_until = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        
        return make_response(jsonify({
            "message": "Código verificado correctamente. Acceso concedido por 10 minutos.",
            "success": True
        }), 200)

api.add_resource(CredentialsOTPRequestResource, '/credentials/request-otp')
api.add_resource(CredentialsOTPVerifyResource, '/credentials/verify-otp')

class SessionCheckResource(Resource):
    @jwt_required()
    def get(self):
        """
        Endpoint para verificar si la sesión actual es válida
        """
        try:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user:
                return make_response(jsonify({
                    'valid': False,
                    'message': 'Usuario no encontrado',
                    'session_expired': True
                }), 401)
            
            # Obtener el token actual
            auth_header = request.headers.get('Authorization', '')
            current_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
            
            # DEBUG: Log información para debuggear
            app.logger.info(f"Session check - User: {user.username}")
            app.logger.info(f"Current token: {current_token[:20] if current_token else None}...")
            app.logger.info(f"Stored token: {user.active_session_token[:20] if user.active_session_token else None}...")
            app.logger.info(f"Tokens match: {user.active_session_token == current_token}")
            
            # Verificar si el token actual coincide con el token activo
            is_valid = (user.active_session_token and 
                       user.active_session_token == current_token)
            
            if is_valid:
                return jsonify({
                    'valid': True,
                    'message': 'Sesión válida',
                    'last_login': user.last_login_at.isoformat() if user.last_login_at else None,
                    'device_info': user.session_device_info,
                    'debug_info': {
                        'token_preview': current_token[:20] + '...' if current_token else None,
                        'stored_preview': user.active_session_token[:20] + '...' if user.active_session_token else None
                    }
                })
            else:
                return make_response(jsonify({
                    'valid': False,
                    'message': 'Tu sesión ha sido cerrada debido a un nuevo inicio de sesión desde otro dispositivo',
                    'session_expired': True,
                    'reason': 'session_replaced',
                    'debug_info': {
                        'current_token_preview': current_token[:20] + '...' if current_token else None,
                        'stored_token_preview': user.active_session_token[:20] + '...' if user.active_session_token else None,
                        'has_stored_token': user.active_session_token is not None
                    }
                }), 401)
                
        except Exception as e:
            return make_response(jsonify({
                'valid': False,
                'message': 'Error al verificar sesión',
                'session_expired': True
            }), 500)

api.add_resource(SessionCheckResource, '/check_session')
    
class CheckIngresosResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        
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

class CheckPagosRecurrentesResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()

        count = PagoRecurrente.query.filter_by(user_id=user.id).count()
        return jsonify({"tiene_pagos_recurrentes": count > 0})

api.add_resource(CheckPagosRecurrentesResource, '/check_pagos_recurrentes')

class RecordatoriosPagosRecurrentesResource(Resource):
    @jwt_required()
    @validate_active_session
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()

        # Obtener pagos recurrentes pendientes
        pagos_pendientes = PagoRecurrente.query.filter_by(user_id=user.id, pagado=False).all()
        fecha_actual = datetime.now()
        sugerencias = []

        for pago in pagos_pendientes:
            sugerencias.append({
                "categoria": pago.categoria,
                "fecha_creacion": pago.fecha_creacion.isoformat(),
                "mensaje": f"Recuerda realizar el pago de {pago.categoria}."
            })

        return jsonify(sugerencias)

api.add_resource(RecordatoriosPagosRecurrentesResource, '/recordatorios_pagos_recurrentes')

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

@app.route('/tarjetas_credito', methods=['GET'])
@jwt_required()
@validate_active_session
def get_tarjetas_credito():
    current_user = get_jwt_identity()
    include_paid = request.args.get('include_paid', 'false').strip().lower() == 'true'  # Ensure proper handling of the parameter
    tarjetas = TarjetaCreditoController.get_tarjetas(int(current_user), include_paid=include_paid)
    return jsonify([tarjeta.to_dict() for tarjeta in tarjetas])

from app.controllers import PagoRecurrenteController  # Ensure this import exists

@app.route('/tarjetas_credito', methods=['POST'])
@jwt_required()
@validate_active_session
def add_tarjeta_credito():
    current_user = get_jwt_identity()
    data = request.get_json()
    
    nueva_tarjeta = TarjetaCreditoController.add_tarjeta(
        user_id=current_user,
        tarjeta_nombre=data['nombre'],
        fecha_corte=data['fechaCorte'],
        fecha_pago=data['fechaPago']
    )
    
    # Add as a recurring payment automatically
    PagoRecurrenteController.add_pago_recurrente(
        user_id=current_user,
        categoria=nueva_tarjeta.tarjeta_nombre
    )
    
    return jsonify(nueva_tarjeta.to_dict()), 201

@app.route('/tarjetas_credito/<int:tarjeta_id>', methods=['DELETE'])
@jwt_required()
@validate_active_session
def delete_tarjeta_credito(tarjeta_id):
    try:
        current_user = get_jwt_identity()
        
        # Verificar que la tarjeta existe y pertenece al usuario
        from app.models import Deuda
        tarjeta = Deuda.query.filter_by(id=tarjeta_id, user_id=current_user).first()
        
        if not tarjeta:
            return jsonify({
                'success': False, 
                'message': 'Tarjeta no encontrada o no tienes permisos para eliminarla'
            }), 404
        
        # Verificar si la tarjeta tiene saldos pendientes
        if tarjeta.saldo_periodo_anterior > 0 or tarjeta.saldo_periodo_actual > 0:
            return jsonify({
                'success': False, 
                'message': 'No se puede eliminar una tarjeta con saldo pendiente'
            }), 400
        
        # Eliminar la tarjeta de pagos recurrentes si existe
        from app.models import PagoRecurrente
        pago_recurrente = PagoRecurrente.query.filter_by(
            user_id=current_user, 
            categoria=tarjeta.tarjeta_nombre
        ).first()
        
        if pago_recurrente:
            db.session.delete(pago_recurrente)
        
        # Eliminar la tarjeta
        db.session.delete(tarjeta)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Tarjeta eliminada correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar tarjeta {tarjeta_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Error interno del servidor'
        }), 500

@app.route('/api/tarjetas_con_ciclo')
@jwt_required()
@validate_active_session
def api_tarjetas_con_ciclo():
    try:
        current_user = get_jwt_identity()
        tarjetas_info = TarjetaCreditoController.get_tarjetas_con_estado_ciclo(current_user)
        return jsonify({
            'success': True,
            'tarjetas': tarjetas_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard_financiero')
@jwt_required()
@validate_active_session
def api_dashboard_financiero():
    try:
        current_user = get_jwt_identity()
        fecha_actual = datetime.now()
        
        # Obtener resumen completo
        resumen = TotalController.get_resumen_financiero_completo(
            current_user, fecha_actual.year, fecha_actual.month
        )
        
        return jsonify({
            'success': True,
            'resumen': resumen
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/procesar_cortes')
@jwt_required()
@validate_active_session
def procesar_cortes():
    try:
        tarjetas_procesadas = TarjetaCreditoController.procesar_corte_mensual()
        return jsonify({
            'success': True, 
            'message': f'{tarjetas_procesadas} tarjetas procesadas'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    app.run()