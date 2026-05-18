from datetime import datetime, timedelta, time
from io import BytesIO

from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.db.models import Max, F, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.roles.permissions import PermisoRequeridoMixin, TienePermiso
from apps.roles.permisos import (
    VER_INVENTARIO,
    EDITAR_PRODUCTO,
    ELIMINAR_PRODUCTO,
    REGISTRAR_MOVIMIENTO,
    VER_HISTORIAL,
    GENERAR_REPORTE,
    GESTIONAR_CATEGORIAS,
)
from apps.tenants.models import TenantModulo
from .models import Categoria, Producto, Movimiento
from .serializers import CategoriaSerializer, ProductoSerializer, MovimientoSerializer



class CategoriaViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_INVENTARIO,
        'retrieve':       VER_INVENTARIO,
        'create':         GESTIONAR_CATEGORIAS,
        'update':         GESTIONAR_CATEGORIAS,
        'partial_update': GESTIONAR_CATEGORIAS,
        'destroy':        GESTIONAR_CATEGORIAS,
    }

    def get_queryset(self):
        return Categoria.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        instance.productos.update(activo=False)
        instance.activo = False
        instance.save()

    @action(detail=True, methods=['post'], url_path='reactivar')
    @transaction.atomic
    def reactivar(self, request, pk=None):
        categoria = self.get_object()
        categoria.activo = True
        categoria.save()
        productos_inactivos = categoria.productos.filter(activo=False)
        return Response({
            'categoria': CategoriaSerializer(categoria).data,
            'productos_inactivos': ProductoSerializer(productos_inactivos, many=True).data,
        })


class ProductoViewSet(PermisoRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':           VER_INVENTARIO,
        'retrieve':       VER_INVENTARIO,
        'create':         EDITAR_PRODUCTO,
        'update':         EDITAR_PRODUCTO,
        'partial_update': EDITAR_PRODUCTO,
        'destroy':        ELIMINAR_PRODUCTO,
    }

    def get_queryset(self):
        return Producto.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save()

    @action(detail=False, methods=['post'], url_path='activar-batch')
    @transaction.atomic
    def activar_batch(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No se proporcionaron IDs.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        activados = Producto.objects.filter(
            id__in=ids,
            tenant=request.user.tenant
        ).update(activo=True)
        return Response({'activados': activados})

    @action(detail=True, methods=['post'], url_path='reactivar')
    def reactivar(self, request, pk=None):
        producto = self.get_object()

        if not producto.categoria.activo:
            return Response(
                {'error': 'La categoría de este producto está inactiva. Ve al dashboard de categorías para activarla primero.'},
                status=status.HTTP_409_CONFLICT
            )

        producto.activo = True
        producto.save()
        return Response(ProductoSerializer(producto).data)


class MovimientoViewSet(PermisoRequeridoMixin,
                        mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = MovimientoSerializer
    permission_classes = [permissions.IsAuthenticated]
    permiso_requerido_map = {
        'list':     VER_HISTORIAL,
        'retrieve': VER_HISTORIAL,
        'create':   REGISTRAR_MOVIMIENTO,
    }

    def get_queryset(self):
        qs = Movimiento.objects.filter(producto__tenant=self.request.user.tenant)
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            qs = qs.filter(producto__id=producto_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard agregado
# ─────────────────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    """
    GET /api/inventory/dashboard/?dias=30

    Devuelve en una sola llamada los cuatro bloques de datos que necesita
    el dashboard:

      1. productos_sin_movimiento      → productos sin entradas/salidas en
                                         los ultimos `dias` (default 30).
      2. productos_bajo_stock_minimo   → productos con stock_actual <
                                         stock_minimo.
      3. servicio                      → fecha de vencimiento + estado del
                                         tenant.
      4. modulos_activos               → modulos contratados activos.

    Optimizaciones:
      - `select_related` para evitar consultas extra por categoria/modulo.
      - `annotate(Max('movimientos__fecha'))` calcula el ultimo movimiento
        en una sola consulta, evitando un N+1 por producto.
      - Cuatro queries totales (productos sin mov, bajo stock, tenant,
        modulos), independientemente del numero de productos/modulos.
    """
    permission_classes = [permissions.IsAuthenticated, TienePermiso]
    permiso_requerido = VER_INVENTARIO

    def get(self, request):
        user = request.user
        tenant = user.tenant
        if tenant is None:
            return Response(
                {'detail': 'El usuario no pertenece a ningun tenant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dias = int(request.query_params.get('dias', 30))
            if dias < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'detail': 'El parametro "dias" debe ser un entero >= 0.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fecha_limite = timezone.now() - timedelta(days=dias)

        # 1) Productos sin movimiento en X dias (incluye los que NUNCA
        #    han tenido movimiento). Una sola query con annotate.
        productos_sin_mov_qs = (
            Producto.objects
            .filter(tenant=tenant, activo=True)
            .select_related('categoria')
            .annotate(ultimo_movimiento=Max('movimientos__fecha'))
            .filter(
                Q(ultimo_movimiento__lt=fecha_limite)
                | Q(ultimo_movimiento__isnull=True)
            )
            .order_by('nombre')
        )

        productos_sin_movimiento = [
            {
                'id':                str(p.id),
                'nombre':            p.nombre,
                'unidad_medida':     p.unidad_medida,
                'stock_actual':      p.stock_actual,
                'stock_minimo':      p.stock_minimo,
                'categoria':         p.categoria.nombre if p.categoria_id else None,
                'ultimo_movimiento': p.ultimo_movimiento,
            }
            for p in productos_sin_mov_qs
        ]

        # 2) Productos por debajo del stock minimo.
        productos_bajo_stock_qs = (
            Producto.objects
            .filter(tenant=tenant, activo=True, stock_actual__lt=F('stock_minimo'))
            .select_related('categoria')
            .order_by('stock_actual')
        )

        productos_bajo_stock = [
            {
                'id':            str(p.id),
                'nombre':        p.nombre,
                'unidad_medida': p.unidad_medida,
                'stock_actual':  p.stock_actual,
                'stock_minimo':  p.stock_minimo,
                'faltante':      p.stock_minimo - p.stock_actual,
                'categoria':     p.categoria.nombre if p.categoria_id else None,
            }
            for p in productos_bajo_stock_qs
        ]

        # 3) Fecha de vencimiento del servicio (del tenant).
        hoy = timezone.localdate()
        dias_restantes = (tenant.fecha_vencimiento - hoy).days
        servicio = {
            'fecha_vencimiento':         tenant.fecha_vencimiento,
            'dias_restantes':            dias_restantes,
            'estado':                    tenant.estado,
            'plan':                      tenant.plan.nombre,
            'vencido':                   dias_restantes < 0,
        }

        # 4) Modulos activos del tenant.
        modulos_qs = (
            TenantModulo.objects
            .filter(tenant=tenant, activo=True)
            .select_related('modulo')
            .order_by('modulo__nombre')
        )
        modulos_activos = [
            {
                'codigo':           tm.modulo.codigo,
                'nombre':           tm.modulo.nombre,
                'label':            tm.modulo.label,
                'icono':            tm.modulo.icono,
                'ruta':             tm.modulo.ruta,
                'fecha_activacion': tm.fecha_activacion,
            }
            for tm in modulos_qs
        ]

        return Response({
            'parametros': {
                'dias': dias,
                'fecha_limite': fecha_limite,
            },
            'productos_sin_movimiento': productos_sin_movimiento,
            'productos_bajo_stock_minimo': productos_bajo_stock,
            'servicio': servicio,
            'modulos_activos': modulos_activos,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Reporte PDF de movimientos
# ─────────────────────────────────────────────────────────────────────────────

class ReporteMovimientosPDFView(APIView):
    """
    GET /api/inventory/reportes/movimientos.pdf/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD

    Genera un PDF descargable con el historial de movimientos del tenant,
    filtrable por rango de fechas. Requiere el permiso `generar_reporte`;
    sin el permiso devuelve 403.

    Parametros (opcionales, ambos inclusivos):
      - desde: fecha de inicio (YYYY-MM-DD). Default: hace 30 dias.
      - hasta: fecha de fin    (YYYY-MM-DD). Default: hoy.
      - producto: UUID de producto para filtrar por uno solo (opcional).
    """
    permission_classes = [permissions.IsAuthenticated, TienePermiso]
    permiso_requerido = GENERAR_REPORTE

    def get(self, request):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )

        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {'detail': 'El usuario no pertenece a ningun tenant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ─── Parseo de fechas ────────────────────────────────────────────
        hoy = timezone.localdate()
        desde_str = request.query_params.get('desde')
        hasta_str = request.query_params.get('hasta')

        if desde_str:
            desde = parse_date(desde_str)
            if desde is None:
                return Response(
                    {'detail': '"desde" debe tener formato YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            desde = hoy - timedelta(days=30)

        if hasta_str:
            hasta = parse_date(hasta_str)
            if hasta is None:
                return Response(
                    {'detail': '"hasta" debe tener formato YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            hasta = hoy

        if desde > hasta:
            return Response(
                {'detail': '"desde" no puede ser mayor que "hasta".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limites en datetime aware para incluir todo el dia "hasta".
        tz = timezone.get_current_timezone()
        desde_dt = timezone.make_aware(datetime.combine(desde, time.min), tz)
        hasta_dt = timezone.make_aware(datetime.combine(hasta, time.max), tz)

        # ─── Query optimizada (sin N+1) ──────────────────────────────────
        movimientos_qs = (
            Movimiento.objects
            .filter(
                producto__tenant=tenant,
                fecha__gte=desde_dt,
                fecha__lte=hasta_dt,
            )
            .select_related('producto', 'usuario')
            .order_by('-fecha')
        )

        producto_id = request.query_params.get('producto')
        if producto_id:
            movimientos_qs = movimientos_qs.filter(producto_id=producto_id)

        # ─── Construccion del PDF ────────────────────────────────────────
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15 * mm, rightMargin=15 * mm,
            topMargin=15 * mm, bottomMargin=15 * mm,
            title='Reporte de Movimientos',
            author=tenant.nombre_negocio,
        )

        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            'titulo', parent=styles['Heading1'],
            alignment=1, fontSize=16, spaceAfter=4,
        )
        sub_style = ParagraphStyle(
            'sub', parent=styles['Normal'],
            alignment=1, fontSize=10, textColor=colors.grey, spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            'meta', parent=styles['Normal'],
            fontSize=9, spaceAfter=10,
        )

        elementos = []
        elementos.append(Paragraph('Reporte de Movimientos de Inventario', titulo_style))
        elementos.append(Paragraph(tenant.nombre_negocio, sub_style))
        elementos.append(Paragraph(
            f'Rango: <b>{desde.isoformat()}</b> a <b>{hasta.isoformat()}</b><br/>'
            f'Generado: {timezone.localtime().strftime("%Y-%m-%d %H:%M")}<br/>'
            f'Solicitado por: {request.user.email}<br/>'
            f'Total de movimientos: <b>{movimientos_qs.count()}</b>',
            meta_style,
        ))

        cabeceras = ['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Motivo', 'Usuario']
        filas = [cabeceras]

        for mov in movimientos_qs:
            filas.append([
                timezone.localtime(mov.fecha).strftime('%Y-%m-%d %H:%M'),
                mov.producto.nombre,
                mov.get_tipo_display(),
                str(mov.cantidad),
                (mov.motivo or '')[:60],
                mov.usuario.email,
            ])

        if len(filas) == 1:
            elementos.append(Paragraph(
                '<i>No se encontraron movimientos en el rango indicado.</i>',
                styles['Normal'],
            ))
        else:
            tabla = Table(
                filas,
                colWidths=[32 * mm, 60 * mm, 22 * mm, 22 * mm, 80 * mm, 50 * mm],
                repeatRows=1,
            )
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0, 0), (-1, 0), 10),
                ('FONTSIZE',   (0, 1), (-1, -1), 8),
                ('ALIGN',      (3, 1), (3, -1), 'RIGHT'),
                ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID',       (0, 0), (-1, -1), 0.25, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                    [colors.whitesmoke, colors.white]),
            ]))
            elementos.append(tabla)

        doc.build(elementos)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        filename = f'movimientos_{desde.isoformat()}_{hasta.isoformat()}.pdf'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = str(len(pdf_bytes))
        return response
