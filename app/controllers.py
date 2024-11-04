#controllers.py
from app import db
from app.models import Ingreso, OtroIngreso, Egreso, PagoRecurrente

# Controlador para manejar los ingresos
class IngresoController:
    @staticmethod
    def get_all_ingresos(user_id):
        return Ingreso.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_ingreso_by_id(ingreso_id):
        return Ingreso.query.get(ingreso_id)

    @staticmethod
    def create_ingreso(fuente, fecha, monto, user_id):
        nuevo_ingreso = Ingreso(fuente=fuente, fecha=fecha, monto=monto, user_id=user_id)
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
    def get_all_egresos(user_id):
        return Egreso.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_egreso_by_id(egreso_id):
        return Egreso.query.get(egreso_id)

    @staticmethod
    def create_egreso(categoria, subcategoria, monto, fecha, user_id, recurrente=False):
        nuevo_egreso = Egreso(categoria=categoria, subcategoria=subcategoria, monto=monto, fecha=fecha, recurrente=recurrente, user_id=user_id)
        db.session.add(nuevo_egreso)
        db.session.commit()
        
        # Marcar el pago recurrente como pagado si corresponde
        pago_recurrente = PagoRecurrente.query.filter_by(user_id=user_id, categoria=categoria).first()
        if pago_recurrente:
            pago_recurrente.pagado = True
            db.session.commit()
        
        return nuevo_egreso

    @staticmethod
    def update_egreso(egreso_id, categoria, subcategoria, monto, fecha, recurrente=False):
        egreso = Egreso.query.get(egreso_id)
        if egreso:
            egreso.categoria = categoria
            egreso.subcategoria = subcategoria
            egreso.monto = monto
            egreso.fecha = fecha
            egreso.recurrente = recurrente
            db.session.commit()
        return egreso

    @staticmethod
    def delete_egreso(egreso_id):
        egreso = Egreso.query.get(egreso_id)
        if egreso:
            db.session.delete(egreso)
            db.session.commit()
        return egreso

    @staticmethod
    def get_total_egresos(user_id):
        total = db.session.query(db.func.sum(Egreso.monto)).filter_by(user_id=user_id).scalar()
        return total or 0
    
class PagoRecurrenteController:
    @staticmethod
    def get_pagos_recurrentes(user_id):
        pagos_recurrentes = PagoRecurrente.query.filter_by(user_id=user_id).all()
        result = []
        for pago in pagos_recurrentes:
            egreso = Egreso.query.filter_by(user_id=user_id, categoria=pago.categoria).order_by(Egreso.fecha.desc()).first()
            monto = float(egreso.monto) if egreso else 0.0
            result.append({
                'id': pago.id,
                'user_id': pago.user_id,
                'categoria': pago.categoria,
                'pagado': pago.pagado,
                'monto': monto,
                'fecha': egreso.fecha if egreso else None
            })
        return result

    @staticmethod
    def add_pago_recurrente(user_id, categoria):
        nuevo_pago_recurrente = PagoRecurrente(user_id=user_id, categoria=categoria)
        db.session.add(nuevo_pago_recurrente)
        db.session.commit()
        return nuevo_pago_recurrente

    @staticmethod
    def delete_pagos_recurrentes(user_id):
        PagoRecurrente.query.filter_by(user_id=user_id).delete()
        db.session.commit()