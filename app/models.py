#models.py
from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)
    otp = db.Column(db.String(6), nullable=True)  # Campo para almacenar el OTP
    otp_expiration = db.Column(db.DateTime, nullable=True)  # Campo para almacenar la fecha de expiración del OTP

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'failed_attempts': self.failed_attempts
        }

class Ingreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fuente = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    descripcion = db.Column(db.String(100), nullable=True)
    user = db.relationship('User', backref=db.backref('ingresos', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'fuente': self.fuente,
            'fecha': self.fecha.isoformat(),
            'monto': str(self.monto),
            'descripcion': self.descripcion,
            'user_id': self.user_id
        }

class OtroIngreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fuente = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    descripcion = db.Column(db.String(70), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('otros_ingresos', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'fuente': self.fuente,
            'fecha': self.fecha.isoformat(),
            'monto': str(self.monto),
            'descripcion': self.descripcion,
            'user_id': self.user_id
        }

class Egreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(255), nullable=False)
    subcategoria = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    recurrente = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bancos = db.Column(db.String(255), nullable=True)  # Nueva columna
    user = db.relationship('User', backref=db.backref('egresos', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'monto': str(self.monto),
            'fecha': self.fecha.isoformat(),
            'recurrente': self.recurrente,
            'user_id': self.user_id,
            'bancos': self.bancos  # Incluir la nueva columna en el diccionario
        }

class PagoRecurrente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    categoria = db.Column(db.String(255), nullable=False)
    pagado = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('pagos_recurrentes', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'categoria': self.categoria,
            'pagado': self.pagado
        }

class Credencial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    credencial = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    eliminado = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('credenciales', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'descripcion': self.descripcion,
            'credencial': self.credencial,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_actualizacion': self.fecha_actualizacion.isoformat(),
            'eliminado': self.eliminado
        }