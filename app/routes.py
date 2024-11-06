#routes.py
from flask import request, jsonify, make_response
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers import IngresoController, OtroIngresoController, EgresoController, PagoRecurrenteController
from app import app, db, api, bcrypt
from app.models import User, Ingreso, OtroIngreso, Egreso, PagoRecurrente
from flask_jwt_extended import create_access_token

@app.route('/')
def index():
    return "Bienvenido a la API de Contabilidad Personal"

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
        if data['fuente'] == 'Ingresos Extras':
            nuevo_otro_ingreso = OtroIngresoController.create_otro_ingreso(data['fuente'], data['fecha'], data['monto'], user.id, data.get('descripcion', ''))
            return jsonify(nuevo_otro_ingreso.to_dict())
        else:
            nuevo_ingreso = IngresoController.create_ingreso(data['fuente'], data['fecha'], data['monto'], user.id)
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
        nuevo_egreso = EgresoController.create_egreso(data['categoria'], data['subcategoria'], data['monto'], data['fecha'], user.id, data.get('recurrente', False))
        return jsonify(nuevo_egreso.to_dict())

api.add_resource(EgresoResource, '/egresos')

class TotalResource(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        
        year = request.args.get('year')
        month = request.args.get('month')
        
        if year and month:
            ingresos = Ingreso.query.filter_by(user_id=user.id).filter(db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).all()
            otros_ingresos = OtroIngreso.query.filter_by(user_id=user.id).filter(db.extract('year', OtroIngreso.fecha) == year, db.extract('month', OtroIngreso.fecha) == month).all()
            egresos = Egreso.query.filter_by(user_id=user.id).filter(db.extract('year', Egreso.fecha) == year, db.extract('month', Egreso.fecha) == month).all()
        else:
            ingresos = Ingreso.query.filter_by(user_id=user.id).all()
            otros_ingresos = OtroIngreso.query.filter_by(user_id=user.id).all()
            egresos = Egreso.query.filter_by(user_id=user.id).all()
        
        total_ingresos = sum([ingreso.monto for ingreso in ingresos])
        total_otros_ingresos = sum([otro_ingreso.monto for otro_ingreso in otros_ingresos])
        total_egresos = sum([egreso.monto for egreso in egresos])
        total = total_ingresos + total_otros_ingresos - total_egresos
        
        return jsonify({
            "total_ingresos": total_ingresos,
            "total_otros_ingresos": total_otros_ingresos,
            "total_egresos": total_egresos,
            "total": total,
            "detalles_ingresos": [ingreso.to_dict() for ingreso in ingresos],
            "detalles_otros_ingresos": [otro_ingreso.to_dict() for otro_ingreso in otros_ingresos],
            "detalles_egresos": [egreso.to_dict() for egreso in egresos]
        })

api.add_resource(TotalResource, '/total')

class RegisterResource(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        if user:
            return make_response(jsonify({"message": "El nombre de usuario ya existe o está en uso. Por favor use otro Nombre de Usuario"}), 400)
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        return make_response(jsonify({"message": "User registered successfully"}), 201)

api.add_resource(RegisterResource, '/register')

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
            access_token = create_access_token(identity={'username': user.username})
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
        pagos_recurrentes = PagoRecurrenteController.get_pagos_recurrentes(user.id)
        return jsonify(pagos_recurrentes)

    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        data = request.get_json()
        categorias = data.get('categorias', [])
        PagoRecurrenteController.delete_pagos_recurrentes(user.id)
        for categoria in categorias:
            PagoRecurrenteController.add_pago_recurrente(user.id, categoria)
        return jsonify({"message": "Pagos recurrentes actualizados"})

api.add_resource(PagoRecurrenteResource, '/pagos_recurrentes')