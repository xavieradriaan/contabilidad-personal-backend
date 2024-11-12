#models.py
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
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
    user = db.relationship('User', backref=db.backref('egresos', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'monto': str(self.monto),
            'fecha': self.fecha.isoformat(),
            'recurrente': self.recurrente,
            'user_id': self.user_id
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