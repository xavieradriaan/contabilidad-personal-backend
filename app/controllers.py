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
            tipo_egreso=tipo_egreso
        )
        db.session.add(nuevo_egreso)
        db.session.commit()

        # Handle "Pago de tarjetas" specifically
        if categoria == 'Pago de tarjetas' and bancos:
            # Buscar TODAS las tarjetas con ese nombre (por si hay duplicados)
            tarjetas = Deuda.query.filter_by(
                user_id=user_id,
                tarjeta_nombre=bancos
            ).all()

            for tarjeta in tarjetas:
                try:
                    # Convertir montos a Decimal para precisión
                    monto_pago = Decimal(str(monto))
                    TarjetaCreditoController.actualizar_estado_tarjeta(
                        tarjeta_id=tarjeta.id,
                        monto_pagado=monto_pago
                    )
                except Exception as e:
                    db.session.rollback()
                    raise Exception(f"Error al actualizar tarjeta {tarjeta.id}: {str(e)}")

            categoria_pago = bancos
        else:
            categoria_pago = categoria

        # Encontrar y actualizar pago recurrente
        pago_recurrente = PagoRecurrente.query.filter_by(
            user_id=user_id,
            categoria=categoria_pago
        ).first()

        if pago_recurrente:
            pago_recurrente.pagado = True
            pago_recurrente.fecha_actualizacion = datetime.utcnow()
            db.session.commit()

        return nuevo_egreso

class PagoRecurrenteController:
    @staticmethod
    def get_pagos_recurrentes(user_id, year, month):
        pagos_recurrentes = PagoRecurrente.query.filter_by(user_id=user_id).all()
        result = []
        for pago in pagos_recurrentes:
            # Match payments by category or bank name for "Pago de tarjetas"
            egresos = Egreso.query.filter(
                Egreso.user_id == user_id,
                (Egreso.categoria == pago.categoria) | 
                ((Egreso.categoria == 'Pago de tarjetas') & (Egreso.bancos == pago.categoria)),
                db.extract('year', Egreso.fecha) == year,
                db.extract('month', Egreso.fecha) == month
            ).all()
            monto = sum(float(egreso.monto) for egreso in egresos if egreso.monto is not None)
            fecha = egresos[0].fecha.isoformat() if egresos else None  # Format date using isoformat()
            result.append({
                'id': pago.id,
                'user_id': pago.user_id,
                'categoria': pago.categoria,
                'pagado': pago.pagado,
                'monto': monto or 0,  # Default to 0 if no amount
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
        ingresos_anteriores = db.session.query(db.func.sum(Ingreso.monto)).filter(
            Ingreso.user_id == user_id, 
            Ingreso.fecha < fecha_actual
        ).scalar() or 0
        
        otros_ingresos_anteriores = db.session.query(db.func.sum(OtroIngreso.monto)).filter(
            OtroIngreso.user_id == user_id, 
            OtroIngreso.fecha < fecha_actual
        ).scalar() or 0
        
        saldo_anterior = ingresos_anteriores + otros_ingresos_anteriores - egresos_anteriores

        # Calcular los ingresos y egresos del mes seleccionado
        ingresos_mes = db.session.query(db.func.sum(Ingreso.monto)).filter(
            Ingreso.user_id == user_id, 
            db.extract('year', Ingreso.fecha) == year, 
            db.extract('month', Ingreso.fecha) == month
        ).scalar() or 0
        
        otros_ingresos_mes = db.session.query(db.func.sum(OtroIngreso.monto)).filter(
            OtroIngreso.user_id == user_id, 
            db.extract('year', OtroIngreso.fecha) == year, 
            db.extract('month', OtroIngreso.fecha) == month
        ).scalar() or 0
        
        # Egresos del mes SIN incluir consumos de crédito
        egresos_mes = db.session.query(db.func.sum(Egreso.monto)).filter(
            Egreso.user_id == user_id, 
            db.extract('year', Egreso.fecha) == year, 
            db.extract('month', Egreso.fecha) == month,
            Egreso.tipo_egreso != 'credito'  # Excluir consumos de crédito
        ).scalar() or 0

        # Calcular el saldo disponible acumulado
        saldo_disponible = saldo_anterior + ingresos_mes + otros_ingresos_mes - egresos_mes
        return saldo_anterior, saldo_disponible

    @staticmethod
    def get_resumen_financiero_completo(user_id, year, month):
        """Nuevo método que proporciona un resumen completo incluyendo tarjetas de crédito"""
        
        # Obtener saldo disponible (dinero real)
        saldo_anterior, saldo_disponible = TotalController.get_saldo_disponible(user_id, year, month)
        
        # Calcular consumos de crédito del mes
        consumos_credito_mes = db.session.query(db.func.sum(Egreso.monto)).filter(
            Egreso.user_id == user_id,
            db.extract('year', Egreso.fecha) == year,
            db.extract('month', Egreso.fecha) == month,
            Egreso.tipo_egreso == 'credito'
        ).scalar() or 0
        
        # Calcular pagos de tarjetas del mes
        pagos_tarjetas_mes = db.session.query(db.func.sum(Egreso.monto)).filter(
            Egreso.user_id == user_id,
            db.extract('year', Egreso.fecha) == year,
            db.extract('month', Egreso.fecha) == month,
            Egreso.categoria == 'Pago de tarjetas'
        ).scalar() or 0
        
        # Obtener información de tarjetas de crédito
        tarjetas_info = TarjetaCreditoController.get_tarjetas_con_estado_ciclo(user_id)
        
        # CALCULAR TOTALES CORRECTAMENTE
        total_deuda_tarjetas = sum(item['saldo_a_pagar'] for item in tarjetas_info)
        total_consumos_periodo = sum(item['consumos_periodo_actual'] for item in tarjetas_info)
        
        # Contar tarjetas por estado
        tarjetas_vencidas = len([t for t in tarjetas_info if t['estado_ciclo'] == 'vencida'])
        tarjetas_por_pagar = len([t for t in tarjetas_info if t['estado_ciclo'] == 'por_pagar'])
        
        # Calcular próximos vencimientos (próximos 7 días)
        from datetime import date, timedelta
        proximos_vencimientos = []
        fecha_limite = date.today() + timedelta(days=7)
        
        for item in tarjetas_info:
            tarjeta_data = item['tarjeta']
            if (tarjeta_data.get('fecha_vencimiento') and 
                date.fromisoformat(tarjeta_data['fecha_vencimiento']) <= fecha_limite and 
                item['saldo_a_pagar'] > 0):
                proximos_vencimientos.append({
                    'nombre': tarjeta_data['tarjeta_nombre'],
                    'monto': item['saldo_a_pagar'],
                    'dias': item['dias_para_vencimiento'],
                    'fecha_vencimiento': tarjeta_data['fecha_vencimiento']
                })
        
        return {
            # Dinero real disponible
            'saldo_anterior': float(saldo_anterior),
            'saldo_disponible': float(saldo_disponible),
            
            # Actividad del mes
            'consumos_credito_mes': float(consumos_credito_mes),
            'pagos_tarjetas_mes': float(pagos_tarjetas_mes),
            
            # Estado de tarjetas
            'total_deuda_tarjetas': float(total_deuda_tarjetas),
            'total_consumos_periodo': float(total_consumos_periodo),
            'tarjetas_vencidas': tarjetas_vencidas,
            'tarjetas_por_pagar': tarjetas_por_pagar,
            
            # Alertas
            'proximos_vencimientos': proximos_vencimientos,
            
            # Métricas adicionales
            'poder_compra_total': float(saldo_disponible),
            'comprometido_tarjetas': float(total_deuda_tarjetas),
            'uso_credito_mes': float(consumos_credito_mes)
        }

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
    def get_tarjetas_con_estado_ciclo(user_id):
        """Obtiene tarjetas con información del ciclo actual"""
        tarjetas = Deuda.query.filter_by(user_id=user_id).all()
        resultado = []
        
        for tarjeta in tarjetas:
            tarjeta.calcular_ciclo_actual()  # Recalcular ciclo
            
            # ✅ CORRECCIÓN: Usar el valor ya guardado en lugar de calcular dinámicamente
            consumos_periodo = float(tarjeta.saldo_periodo_actual or 0)
            
            # Calcular pagos del periodo (esto sí necesita cálculo dinámico)
            pagos_periodo = db.session.query(db.func.sum(Egreso.monto)).filter(
                Egreso.user_id == user_id,
                Egreso.categoria == 'Pago de tarjetas',
                Egreso.bancos == tarjeta.tarjeta_nombre,
                Egreso.fecha >= tarjeta.ciclo_actual_inicio
            ).scalar() or 0
            
            # NUEVA LÓGICA DE ESTADO CORREGIDA
            from datetime import date
            hoy = date.today()
            
            # Calcular el día de corte y pago del mes actual
            try:
                corte_mes_actual = date(hoy.year, hoy.month, tarjeta.fecha_corte)
            except ValueError:
                from calendar import monthrange
                ultimo_dia = monthrange(hoy.year, hoy.month)[1]
                corte_mes_actual = date(hoy.year, hoy.month, min(tarjeta.fecha_corte, ultimo_dia))
            
            # Calcular fecha de pago
            if tarjeta.fecha_pago < tarjeta.fecha_corte:
                # Pago es el siguiente mes
                if corte_mes_actual.month == 12:
                    año_pago = corte_mes_actual.year + 1
                    mes_pago = 1
                else:
                    año_pago = corte_mes_actual.year
                    mes_pago = corte_mes_actual.month + 1
                
                try:
                    fecha_pago_mes = date(año_pago, mes_pago, tarjeta.fecha_pago)
                except ValueError:
                    from calendar import monthrange
                    ultimo_dia_pago = monthrange(año_pago, mes_pago)[1]
                    fecha_pago_mes = date(año_pago, mes_pago, min(tarjeta.fecha_pago, ultimo_dia_pago))
            else:
                # Pago es el mismo mes
                try:
                    fecha_pago_mes = date(hoy.year, hoy.month, tarjeta.fecha_pago)
                except ValueError:
                    from calendar import monthrange
                    ultimo_dia_pago = monthrange(hoy.year, hoy.month)[1]
                    fecha_pago_mes = date(hoy.year, hoy.month, min(tarjeta.fecha_pago, ultimo_dia_pago))
            
            # DETERMINAR ESTADO REAL (LÓGICA COMPLETAMENTE CORREGIDA)
            saldo_anterior = float(tarjeta.saldo_periodo_anterior or 0)
            
            if saldo_anterior <= 0 and tarjeta.pagada:
                # NO hay deuda cortada pendiente, determinar por ciclo actual
                if hoy < corte_mes_actual:
                    estado_ciclo = "en_curso"
                    dias_para_corte = (corte_mes_actual - hoy).days
                    dias_para_vencimiento = (fecha_pago_mes - hoy).days
                else:
                    # Ya pasó el corte, pero no hay deuda anterior = está al día
                    estado_ciclo = "al_dia"
                    dias_para_corte = 0
                    dias_para_vencimiento = (fecha_pago_mes - hoy).days if hoy <= fecha_pago_mes else 0
            elif saldo_anterior > 0 and not tarjeta.pagada:
                # HAY deuda cortada sin pagar
                if hoy <= fecha_pago_mes:
                    estado_ciclo = "por_pagar"
                    dias_para_corte = 0
                    dias_para_vencimiento = (fecha_pago_mes - hoy).days
                else:
                    estado_ciclo = "vencida"
                    dias_para_corte = 0
                    dias_para_vencimiento = 0
            else:
                # Casos especiales - usar fechas como fallback
                if hoy < corte_mes_actual:
                    estado_ciclo = "en_curso"
                    dias_para_corte = (corte_mes_actual - hoy).days
                    dias_para_vencimiento = (fecha_pago_mes - hoy).days
                elif hoy <= fecha_pago_mes:
                    estado_ciclo = "por_pagar"
                    dias_para_corte = 0
                    dias_para_vencimiento = (fecha_pago_mes - hoy).days
                else:
                    estado_ciclo = "vencida"
                    dias_para_corte = 0
                    dias_para_vencimiento = 0
            
            # CALCULAR SALDO TOTAL A PAGAR CORRECTAMENTE
            saldo_total = float(tarjeta.saldo_periodo_anterior or 0) + consumos_periodo
            
            resultado.append({
                'tarjeta': tarjeta.to_dict(),
                'consumos_periodo_actual': consumos_periodo,  # ✅ Ahora usa el valor correcto
                'pagos_realizados': float(pagos_periodo),
                'estado_ciclo': estado_ciclo,
                'dias_para_corte': max(0, dias_para_corte),
                'dias_para_vencimiento': max(0, dias_para_vencimiento),
                'saldo_a_pagar': saldo_total
            })
        
        return resultado

    @staticmethod
    def get_tarjetas(user_id, include_paid=False):
        query = Deuda.query.filter_by(user_id=user_id)
        if not include_paid:
            query = query.filter_by(pagada=False)
        return query.order_by(Deuda.fecha_pago).all()  # Sort by fecha_pago

    @staticmethod
    def add_tarjeta(user_id, tarjeta_nombre, fecha_corte, fecha_pago, subcategoria=None):
        from datetime import datetime
        
        # Extraer el día de la fecha si viene como string de fecha completa
        if isinstance(fecha_corte, str):
            if '-' in fecha_corte:  # Formato de fecha completa (YYYY-MM-DD)
                fecha_corte_obj = datetime.strptime(fecha_corte, '%Y-%m-%d')
                dia_corte = fecha_corte_obj.day
            else:  # Ya es solo el día
                dia_corte = int(fecha_corte)
        else:
            dia_corte = int(fecha_corte)
            
        if isinstance(fecha_pago, str):
            if '-' in fecha_pago:  # Formato de fecha completa (YYYY-MM-DD)
                fecha_pago_obj = datetime.strptime(fecha_pago, '%Y-%m-%d')
                dia_pago = fecha_pago_obj.day
            else:  # Ya es solo el día
                dia_pago = int(fecha_pago)
        else:
            dia_pago = int(fecha_pago)
        
        nueva_tarjeta = Deuda(
            user_id=user_id,
            tarjeta_nombre=tarjeta_nombre,
            fecha_corte=dia_corte,  # Usar el día extraído
            fecha_pago=dia_pago,    # Usar el día extraído
            monto=0,
            pagada=True,  # Empezar como pagada (sin deuda cortada)
            saldo_periodo_anterior=0,
            saldo_periodo_actual=0
        )
        if subcategoria:
            nueva_tarjeta.subcategoria = subcategoria
        
        nueva_tarjeta.calcular_ciclo_actual()
        db.session.add(nueva_tarjeta)
        db.session.commit()
        return nueva_tarjeta

    @staticmethod
    def get_tarjeta_by_nombre(tarjeta_nombre, user_id):
        return Deuda.query.filter_by(tarjeta_nombre=tarjeta_nombre, user_id=user_id).first()

    @staticmethod
    def registrar_consumo(tarjeta_id, monto):
        try:
            tarjeta = Deuda.query.get(tarjeta_id)
            if not tarjeta:
                raise ValueError("La tarjeta especificada no existe.")
            
            monto = Decimal(monto)
            
            # Los consumos SIEMPRE van al periodo actual
            tarjeta.saldo_periodo_actual += monto
            
            # Actualizar monto total
            tarjeta.monto = tarjeta.saldo_periodo_anterior + tarjeta.saldo_periodo_actual
            
            # NO cambiar el estado "pagada" por consumos del periodo actual
            # tarjeta.pagada refleja solo el estado del periodo cortado
                
            db.session.commit()
            return tarjeta
        except Exception:
            raise

    @staticmethod
    def actualizar_estado_tarjeta(tarjeta_id, monto_pagado):
        tarjeta = Deuda.query.get(tarjeta_id)
        if not tarjeta:
            raise ValueError("Tarjeta no existe")
        
        if monto_pagado <= Decimal('0'):
            raise ValueError("Monto de pago inválido")

        # Recalcular ciclo actual primero
        tarjeta.calcular_ciclo_actual()
        
        # Aplicar pago al saldo del periodo anterior primero
        if tarjeta.saldo_periodo_anterior > Decimal('0'):
            if monto_pagado >= tarjeta.saldo_periodo_anterior:
                # Pago cubre toda la deuda del periodo anterior
                exceso = monto_pagado - tarjeta.saldo_periodo_anterior
                tarjeta.saldo_periodo_anterior = Decimal('0')
                tarjeta.pagada = True
                
                # Si hay exceso, aplicar al periodo actual
                if exceso > Decimal('0') and tarjeta.saldo_periodo_actual > Decimal('0'):
                    tarjeta.saldo_periodo_actual = max(Decimal('0'), 
                                                     tarjeta.saldo_periodo_actual - exceso)
            else:
                # Pago parcial del periodo anterior
                tarjeta.saldo_periodo_anterior -= monto_pagado
                tarjeta.pagada = False
        else:
            # No hay deuda del periodo anterior, aplicar al actual
            tarjeta.saldo_periodo_actual = max(Decimal('0'), 
                                             tarjeta.saldo_periodo_actual - monto_pagado)
            tarjeta.pagada = True  # El periodo cortado está pagado
        
        # Actualizar monto total
        tarjeta.monto = tarjeta.saldo_periodo_anterior + tarjeta.saldo_periodo_actual
        
        db.session.commit()

    @staticmethod
    def procesar_corte_mensual():
        """Procesa el corte mensual - se ejecuta automáticamente"""
        from datetime import date
        
        hoy = date.today()
        tarjetas = Deuda.query.filter_by(fecha_corte=hoy.day).all()
        
        for tarjeta in tarjetas:
            # Mover el saldo actual al periodo anterior (nuevo corte)
            tarjeta.saldo_periodo_anterior = tarjeta.saldo_periodo_actual
            tarjeta.saldo_periodo_actual = Decimal('0')
            
            # Ahora HAY nueva deuda cortada, por lo tanto no está pagada
            tarjeta.pagada = tarjeta.saldo_periodo_anterior <= Decimal('0')
            
            # Actualizar monto total y ciclo
            tarjeta.monto = tarjeta.saldo_periodo_anterior + tarjeta.saldo_periodo_actual
            tarjeta.calcular_ciclo_actual()
            
        db.session.commit()
        return len(tarjetas)

# Función para el scheduler (debe ser llamada desde app.py o __init__.py)
def setup_scheduler_jobs():
    """Esta función debe ser llamada desde donde se inicializa el scheduler"""
    from app import app, scheduler
    
    def procesar_cortes_automatico():
        with app.app_context():
            TarjetaCreditoController.procesar_corte_mensual()
            app.logger.info("Cortes de tarjetas procesados")

    # Agregar nueva tarea al scheduler
    scheduler.add_job(
        func=procesar_cortes_automatico,
        trigger='cron',
        hour=0,  # Ejecutar a medianoche
        minute=1
    )