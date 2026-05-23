# apps/tenants/management/commands/verificar_vencimientos.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
from apps.tenants.models import Tenant
from apps.notifications.models import Notificacion

class Command(BaseCommand):
    help = 'Revisa vencimientos, genera notificaciones en BD y envía correos electrónicos'

    def handle(self, *args, **options):
        hoy = date.today()
        limite_aviso = hoy + timedelta(days=7)
        
        tenants_por_vencer = Tenant.objects.filter(
            estado=Tenant.Estado.ACTIVO,
            fecha_vencimiento__range=[hoy, limite_aviso]
        )
        
        conteo_notificaciones = 0
        conteo_correos = 0
        
        for tenant in tenants_por_vencer:
            dias_restantes = (tenant.fecha_vencimiento - hoy).days
            
            # 1. Definir los mensajes según los días restantes
            if dias_restantes == 0:
                asunto_email = f"⚠️ ¡URGENTE! Tu suscripción ha vencido HOY - {tenant.nombre_negocio}"
                mensaje = f"¡Atención! Tu suscripción al plan '{tenant.plan.nombre}' ha vencido HOY. Realiza tu pago para evitar la suspensión."
            else:
                asunto_email = f"⏳ Recordatorio de vencimiento de plan - {tenant.nombre_negocio}"
                mensaje = f"Recordatorio: Tu suscripción al plan '{tenant.plan.nombre}' vencerá en {dias_restantes} días ({tenant.fecha_vencimiento})."
            
            # 2. Verificar duplicados en la Base de Datos para el día de hoy
            notificacion_existe = Notificacion.objects.filter(
                tenant=tenant,
                tipo='vencimiento_cuenta',
                created_at__date=hoy
            ).exists()

            if not notificacion_existe:
                # Crear notificación en el sistema (Base de Datos)
                Notificacion.objects.create(
                    tenant=tenant,
                    tipo='vencimiento_cuenta',
                    modulo='sistema',
                    mensaje=mensaje,
                    leida=False
                )
                conteo_notificaciones += 1

                # 3. Enviar Correo Electrónico al email_contacto del Tenant
                try:
                    send_mail(
                        subject=asunto_email,
                        message=mensaje,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tusistema.com'),
                        recipient_list=[tenant.email_contacto],
                        fail_silently=False, # Ponemos False para capturar el error si falla
                    )
                    conteo_correos += 1
                    self.stdout.write(f"Correo enviado con éxito a: {tenant.email_contacto}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error al enviar correo a {tenant.email_contacto}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(
            f'Proceso terminado. Se crearon {conteo_notificaciones} notificaciones en BD y se enviaron {conteo_correos} correos.'
        ))