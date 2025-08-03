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
    
    # Campos para verificación de acceso a credenciales
    credentials_otp = db.Column(db.String(6), nullable=True)  # OTP para acceso a credenciales
    credentials_otp_expiration = db.Column(db.DateTime, nullable=True)  # Expiración del OTP de credenciales
    credentials_session_valid_until = db.Column(db.DateTime, nullable=True)  # Sesión válida hasta esta fecha

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
    tipo_egreso = db.Column(db.String(50), nullable=False, default='debito')  # Puede ser 'debito' o 'credito'
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
            'bancos': self.bancos,  # Incluir la nueva columna en el diccionario
            'tipo_egreso': self.tipo_egreso  # Asegurar que este campo se incluya
        }

class PagoRecurrente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    categoria = db.Column(db.String(255), nullable=False)
    pagado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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

class Deuda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tarjeta_nombre = db.Column(db.String(255), nullable=False)
    # Cambiar estos campos de Date a Integer (día del mes)
    fecha_corte = db.Column(db.Integer, nullable=False)  # Día del mes (1-31)
    fecha_pago = db.Column(db.Integer, nullable=False)   # Día del mes (1-31)
    monto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pagada = db.Column(db.Boolean, default=False)
    
    # Nuevos campos para el sistema de ciclos
    ciclo_actual_inicio = db.Column(db.Date)
    ciclo_actual_fin = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    saldo_periodo_anterior = db.Column(db.Numeric(10, 2), default=0)
    saldo_periodo_actual = db.Column(db.Numeric(10, 2), default=0)
    
    user = db.relationship('User', backref=db.backref('deudas', lazy=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.fecha_corte and self.fecha_pago:
            self.calcular_ciclo_actual()

    def calcular_ciclo_actual(self):
        from datetime import date, timedelta
        from calendar import monthrange
        
        hoy = date.today()
        
        # Calcular fecha de corte del mes actual
        try:
            corte_mes_actual = date(hoy.year, hoy.month, self.fecha_corte)
        except ValueError:
            ultimo_dia = monthrange(hoy.year, hoy.month)[1]
            corte_mes_actual = date(hoy.year, hoy.month, min(self.fecha_corte, ultimo_dia))
        
        # LÓGICA CORREGIDA PARA CICLOS
        if hoy <= corte_mes_actual:
            # Estamos en el periodo actual (antes del corte)
            # El ciclo comenzó el mes pasado después del corte
            if hoy.month == 1:
                mes_anterior = 12
                año_anterior = hoy.year - 1
            else:
                mes_anterior = hoy.month - 1
                año_anterior = hoy.year
            
            try:
                corte_anterior = date(año_anterior, mes_anterior, self.fecha_corte)
                self.ciclo_actual_inicio = corte_anterior + timedelta(days=1)
            except ValueError:
                ultimo_dia_anterior = monthrange(año_anterior, mes_anterior)[1]
                corte_anterior = date(año_anterior, mes_anterior, min(self.fecha_corte, ultimo_dia_anterior))
                self.ciclo_actual_inicio = corte_anterior + timedelta(days=1)
            
            self.ciclo_actual_fin = corte_mes_actual
        else:
            # Ya pasó el corte, estamos en el nuevo periodo
            self.ciclo_actual_inicio = corte_mes_actual + timedelta(days=1)
            
            # Calcular próximo corte
            if hoy.month == 12:
                mes_siguiente = 1
                año_siguiente = hoy.year + 1
            else:
                mes_siguiente = hoy.month + 1
                año_siguiente = hoy.year
            
            try:
                self.ciclo_actual_fin = date(año_siguiente, mes_siguiente, self.fecha_corte)
            except ValueError:
                ultimo_dia_siguiente = monthrange(año_siguiente, mes_siguiente)[1]
                self.ciclo_actual_fin = date(año_siguiente, mes_siguiente, min(self.fecha_corte, ultimo_dia_siguiente))
        
        # Calcular fecha de vencimiento
        if self.fecha_pago < self.fecha_corte:
            # Pago el siguiente mes después del corte
            if self.ciclo_actual_fin.month == 12:
                año_vencimiento = self.ciclo_actual_fin.year + 1
                mes_vencimiento = 1
            else:
                año_vencimiento = self.ciclo_actual_fin.year
                mes_vencimiento = self.ciclo_actual_fin.month + 1
        else:
            # Pago el mismo mes del corte
            año_vencimiento = self.ciclo_actual_fin.year
            mes_vencimiento = self.ciclo_actual_fin.month
        
        try:
            self.fecha_vencimiento = date(año_vencimiento, mes_vencimiento, self.fecha_pago)
        except ValueError:
            ultimo_dia_vencimiento = monthrange(año_vencimiento, mes_vencimiento)[1]
            self.fecha_vencimiento = date(año_vencimiento, mes_vencimiento, min(self.fecha_pago, ultimo_dia_vencimiento))

    def to_dict(self):
        return {
            'id': self.id,
            'tarjeta_nombre': self.tarjeta_nombre,
            'fecha_corte': self.fecha_corte,  # Ahora es un entero
            'fecha_pago': self.fecha_pago,    # Ahora es un entero
            'monto': str(self.monto),
            'user_id': self.user_id,
            'pagada': self.pagada,
            'saldo_periodo_anterior': str(self.saldo_periodo_anterior),
            'saldo_periodo_actual': str(self.saldo_periodo_actual),
            'ciclo_actual_inicio': self.ciclo_actual_inicio.isoformat() if self.ciclo_actual_inicio else None,
            'ciclo_actual_fin': self.ciclo_actual_fin.isoformat() if self.ciclo_actual_fin else None,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None
        }