# controllers.py
from app import db
from app.models import Ingreso, OtroIngreso, Egreso, PagoRecurrente
from datetime import datetime

# Controlador para manejar los ingresos
class IngresoController:
    @staticmethod
    def get_all_ingresos(user_id):
        return Ingreso.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_ingreso_by_id(ingreso_id):
        return Ingreso.query.get(ingreso_id)

    @staticmethod
    def create_ingreso(fuente, fecha, monto, user_id, descripcion=''):
        nuevo_ingreso = Ingreso(fuente=fuente, fecha=fecha, monto=monto, user_id=user_id, descripcion=descripcion)
        db.session.add(nuevo_ingreso)
        db.session.commit()
        return nuevo_ingreso

    @staticmethod
    def update_ingreso(ingreso_id, fuente, fecha, monto):
        ingreso = Ingreso.query.get(ingreso_id)
        if ingreso:
            ingreso.fuente = fuente
            ingreso.fecha = fecha
            ingreso.monto = monto
            db.session.commit()
        return ingreso

    @staticmethod
    def delete_ingreso(ingreso_id):
        ingreso = Ingreso.query.get(ingreso_id)
        if ingreso:
            db.session.delete(ingreso)
            db.session.commit()
        return ingreso

    @staticmethod
    def get_total_ingresos(user_id):
        total = db.session.query(db.func.sum(Ingreso.monto)).filter_by(user_id=user_id).scalar()
        return total or 0

# Controlador para manejar otros ingresos
class OtroIngresoController:
    @staticmethod
    def create_otro_ingreso(fuente, fecha, monto, user_id, descripcion=''):
        nuevo_otro_ingreso = OtroIngreso(fuente=fuente, fecha=fecha, monto=monto, user_id=user_id, descripcion=descripcion)
        db.session.add(nuevo_otro_ingreso)
        db.session.commit()
        return nuevo_otro_ingreso

    @staticmethod
    def get_otro_ingreso_by_id(otro_ingreso_id):
        return OtroIngreso.query.get(otro_ingreso_id)

    @staticmethod
    def update_otro_ingreso(otro_ingreso_id, fuente, fecha, monto, descripcion=''):
        otro_ingreso = OtroIngreso.query.get(otro_ingreso_id)
        if otro_ingreso:
            otro_ingreso.fuente = fuente
            otro_ingreso.fecha = fecha
            otro_ingreso.monto = monto
            otro_ingreso.descripcion = descripcion
            db.session.commit()
        return otro_ingreso

    @staticmethod
    def delete_otro_ingreso(otro_ingreso_id):
        otro_ingreso = OtroIngreso.query.get(otro_ingreso_id)
        if otro_ingreso:
            db.session.delete(otro_ingreso)
            db.session.commit()
        return otro_ingreso

    @staticmethod
    def get_total_otros_ingresos(user_id):
        total = db.session.query(db.func.sum(OtroIngreso.monto)).filter_by(user_id=user_id).scalar()
        return total or 0

# Controlador para manejar los egresos
class EgresoController:
    @staticmethod
    def create_egreso(categoria, subcategoria, monto, fecha, user_id, bancos=None, recurrente=False):
        nuevo_egreso = Egreso(
            categoria=categoria,
            subcategoria=subcategoria,
            monto=monto,
            fecha=fecha,
            user_id=user_id,
            bancos=bancos,
            recurrente=recurrente
        )
        db.session.add(nuevo_egreso)
        db.session.commit()
        
        # Marcar el pago recurrente como pagado si corresponde
        pago_recurrente = PagoRecurrente.query.filter_by(user_id=user_id, categoria=categoria).first()
        if pago_recurrente:
            pago_recurrente.pagado = True
            db.session.commit()
        
        return nuevo_egreso

class PagoRecurrenteController:
    @staticmethod
    def get_pagos_recurrentes(user_id, year, month):
        pagos_recurrentes = PagoRecurrente.query.filter_by(user_id=user_id).all()
        result = []
        for pago in pagos_recurrentes:
            egresos = Egreso.query.filter_by(user_id=user_id, categoria=pago.categoria).filter(
                db.extract('year', Egreso.fecha) == year,
                db.extract('month', Egreso.fecha) == month
            ).all()
            monto = sum(float(egreso.monto) for egreso in egresos if egreso.monto is not None)
            result.append({
                'id': pago.id,
                'user_id': pago.user_id,
                'categoria': pago.categoria,
                'pagado': pago.pagado,
                'monto': monto,
                'fecha': egresos[0].fecha if egresos else None
            })
        return result

    @staticmethod
    def reset_pagos_recurrentes():
        pagos_recurrentes = PagoRecurrente.query.all()
        for pago in pagos_recurrentes:
            pago.pagado = False
        db.session.commit()

    @staticmethod
    def add_pago_recurrente(user_id, categoria):
        existing_pago = PagoRecurrente.query.filter_by(user_id=user_id, categoria=categoria).first()
        if not existing_pago:
            nuevo_pago_recurrente = PagoRecurrente(user_id=user_id, categoria=categoria)
            db.session.add(nuevo_pago_recurrente)
            db.session.commit()
            return nuevo_pago_recurrente
        return existing_pago

    @staticmethod
    def save_pagos_recurrentes(user_id, categorias):
        for categoria in categorias:
            PagoRecurrenteController.add_pago_recurrente(user_id, categoria)

# Controlador para manejar el saldo disponible
class TotalController:
    @staticmethod
    def get_saldo_disponible(user_id, year, month):
        # Calcular el saldo disponible acumulado de meses anteriores
        fecha_actual = datetime(year, month, 1)
        ingresos_anteriores = db.session.query(db.func.sum(Ingreso.monto)).filter(Ingreso.user_id == user_id, Ingreso.fecha < fecha_actual).scalar() or 0
        otros_ingresos_anteriores = db.session.query(db.func.sum(OtroIngreso.monto)).filter(OtroIngreso.user_id == user_id, OtroIngreso.fecha < fecha_actual).scalar() or 0
        egresos_anteriores = db.session.query(db.func.sum(Egreso.monto)).filter(Egreso.user_id == user_id, Egreso.fecha < fecha_actual).scalar() or 0
        saldo_anterior = ingresos_anteriores + otros_ingresos_anteriores - egresos_anteriores

        # Calcular los ingresos y egresos del mes seleccionado
        ingresos_mes = db.session.query(db.func.sum(Ingreso.monto)).filter(Ingreso.user_id == user_id, db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).scalar() or 0
        otros_ingresos_mes = db.session.query(db.func.sum(OtroIngreso.monto)).filter(OtroIngreso.user_id == user_id, db.extract('year', OtroIngreso.fecha) == year, db.extract('month', OtroIngreso.fecha) == month).scalar() or 0
        egresos_mes = db.session.query(db.func.sum(Egreso.monto)).filter(Egreso.user_id == user_id, db.extract('year', Egreso.fecha) == year, db.extract('month', Egreso.fecha) == month).scalar() or 0

        # Calcular el saldo disponible acumulado
        saldo_disponible = saldo_anterior + ingresos_mes + otros_ingresos_mes - egresos_mes
        return saldo_anterior, saldo_disponible