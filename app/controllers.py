# controllers.py
from app import db
from app.models import Ingreso, OtroIngreso, Egreso, PagoRecurrente, Credencial
from datetime import datetime
import os
from app.models import Deuda
from decimal import Decimal

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
    def get_all_egresos(user_id):
        return Egreso.query.filter_by(user_id=user_id).all()

    @staticmethod
    def create_egreso(categoria, subcategoria, monto, fecha, user_id, bancos=None, recurrente=False, tipo_egreso='debito'):
        nuevo_egreso = Egreso(
            categoria=categoria,
            subcategoria=subcategoria,
            monto=monto,
            fecha=fecha,
            user_id=user_id,
            bancos=bancos,
            recurrente=recurrente,
            tipo_egreso=tipo_egreso  # Agregar tipo_egreso al modelo
        )
        db.session.add(nuevo_egreso)
        db.session.commit()
        
        # Marcar el pago recurrente como pagado si corresponde
        pago_recurrente = PagoRecurrente.query.filter_by(user_id=user_id, categoria=categoria).first()
        if pago_recurrente:
            pago_recurrente.pagado = True
            pago_recurrente.fecha_actualizacion = datetime.utcnow()  # Actualizar la fecha de actualización
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
            fecha = egresos[0].fecha if egresos else None
            result.append({
                'id': pago.id,
                'user_id': pago.user_id,
                'categoria': pago.categoria,
                'pagado': pago.pagado,
                'monto': monto or 0,  # Si no hay monto, devuelve 0
                'fecha': fecha
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
        # Limpiar selecciones anteriores
        PagoRecurrente.query.filter_by(user_id=user_id).delete()

        # Agregar nuevas categorías
        for categoria in categorias:
            nuevo_pago = PagoRecurrente(user_id=user_id, categoria=categoria)
            db.session.add(nuevo_pago)

        db.session.commit()
          
# Controlador para manejar el saldo disponible
# Controlador para manejar el saldo disponible
class TotalController:
    @staticmethod
    def get_saldo_disponible(user_id, year, month):
        fecha_actual = datetime(year, month, 1)

        # Calcular saldo anterior excluyendo crédito
        egresos_anteriores = db.session.query(db.func.sum(Egreso.monto)).filter(
            Egreso.user_id == user_id,
            Egreso.fecha < fecha_actual,
            Egreso.tipo_egreso != 'credito'  # Excluir crédito
        ).scalar() or 0

        # Calcular el saldo disponible acumulado de meses anteriores
        ingresos_anteriores = db.session.query(db.func.sum(Ingreso.monto)).filter(Ingreso.user_id == user_id, Ingreso.fecha < fecha_actual).scalar() or 0
        otros_ingresos_anteriores = db.session.query(db.func.sum(OtroIngreso.monto)).filter(OtroIngreso.user_id == user_id, OtroIngreso.fecha < fecha_actual).scalar() or 0
        saldo_anterior = ingresos_anteriores + otros_ingresos_anteriores - egresos_anteriores

        # Calcular los ingresos y egresos del mes seleccionado
        ingresos_mes = db.session.query(db.func.sum(Ingreso.monto)).filter(Ingreso.user_id == user_id, db.extract('year', Ingreso.fecha) == year, db.extract('month', Ingreso.fecha) == month).scalar() or 0
        otros_ingresos_mes = db.session.query(db.func.sum(OtroIngreso.monto)).filter(OtroIngreso.user_id == user_id, db.extract('year', OtroIngreso.fecha) == year, db.extract('month', OtroIngreso.fecha) == month).scalar() or 0
        egresos_mes = db.session.query(db.func.sum(Egreso.monto)).filter(Egreso.user_id == user_id, db.extract('year', Egreso.fecha) == year, db.extract('month', Egreso.fecha) == month).scalar() or 0

        # Calcular el saldo disponible acumulado
        saldo_disponible = saldo_anterior + ingresos_mes + otros_ingresos_mes - egresos_mes
        return saldo_anterior, saldo_disponible

# Controlador para manejar las credenciales
class CredencialController:
    @staticmethod
    def get_credenciales(user_id):
        return Credencial.query.filter_by(user_id=user_id).all()

    @staticmethod
    def create_credencial(user_id, descripcion, credencial):
        nueva_credencial = Credencial(user_id=user_id, descripcion=descripcion, credencial=credencial)
        db.session.add(nueva_credencial)
        db.session.commit()
        return nueva_credencial

    @staticmethod
    def update_credencial(credencial_id, descripcion, credencial):
        credencial = Credencial.query.get(credencial_id)
        if credencial:
            credencial.descripcion = descripcion
            credencial.credencial = credencial
            db.session.commit()
        return credencial

    @staticmethod
    def delete_credencial(credencial_id):
        credencial = Credencial.query.get(credencial_id)
        if credencial:
            db.session.delete(credencial)
            db.session.commit()
        return credencial

class TarjetaCreditoController:
    @staticmethod
    def get_tarjetas(user_id, include_paid=False):
        query = Deuda.query.filter_by(user_id=user_id)
        if not include_paid:
            query = query.filter_by(pagada=False)
        return query.order_by(Deuda.fecha_pago).all()  # Sort by fecha_pago

    @staticmethod
    def add_tarjeta(user_id, tarjeta_nombre, fecha_corte, fecha_pago, subcategoria=None):
        nueva_tarjeta = Deuda(
            user_id=user_id,
            tarjeta_nombre=tarjeta_nombre,
            fecha_corte=fecha_corte,
            fecha_pago=fecha_pago,
            monto=0,
            pagada=False
        )
        if subcategoria:  # Save subcategoria if provided
            nueva_tarjeta.subcategoria = subcategoria
        db.session.add(nueva_tarjeta)
        db.session.commit()
        return nueva_tarjeta

    @staticmethod
    def get_tarjeta_by_nombre(tarjeta_nombre, user_id):
        return Deuda.query.filter_by(tarjeta_nombre=tarjeta_nombre, user_id=user_id, pagada=False).first()

    @staticmethod
    def registrar_consumo(tarjeta_id, monto):
        tarjeta = Deuda.query.get(tarjeta_id)
        if tarjeta:
            # Convert monto to Decimal for consistency
            monto = Decimal(monto)
            tarjeta.monto += monto
            db.session.commit()
            return tarjeta
        else:
            raise ValueError("La tarjeta especificada no existe.")

    @staticmethod
    def actualizar_estado_tarjeta(tarjeta_id, monto_pagado):
        tarjeta = Deuda.query.get(tarjeta_id)
        if not tarjeta:
            raise ValueError("La tarjeta especificada no existe.")
        
        # Convert monto_pagado to Decimal for consistency
        monto_pagado = Decimal(monto_pagado)
        
        # Update the card's balance
        tarjeta.monto -= monto_pagado
        
        # Mark the card as paid if the balance is zero or less
        if tarjeta.monto <= 0:
            tarjeta.monto = 0
            tarjeta.pagada = True
        
        db.session.commit()
        return tarjeta