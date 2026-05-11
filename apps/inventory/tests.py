# apps/inventory/tests.py
"""
Tests de autorizacion sobre el modulo de inventario.

Verifican el criterio de aceptacion definido por el usuario:
"un usuario sin el permiso `editar_producto` recibe 403 al intentar
modificar un producto, y esto aplica en todos los endpoints relevantes".

Estos tests tambien cubren tenant isolation (NFR01) — un usuario nunca
puede operar sobre productos de otro tenant ni siquiera con el permiso.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Plan, Tenant
from apps.roles.models import Permiso, Rol
from apps.roles.permisos import (
    EDITAR_PRODUCTO,
    ELIMINAR_PRODUCTO,
    REGISTRAR_MOVIMIENTO,
    VER_INVENTARIO,
)
from apps.users.models import Usuario
from .models import Categoria, Producto


def _crear_tenant(nombre='Negocio Test'):
    plan, _ = Plan.objects.get_or_create(
        nombre='Test',
        defaults={
            'max_usuarios': 10,
            'max_productos': 100,
            'max_categorias': 10,
            'precio_mensual': 0,
        },
    )
    return Tenant.objects.create(
        plan=plan,
        nombre_negocio=nombre,
        email_contacto=f'{nombre.lower().replace(" ", "")}@test.local',
        fecha_vencimiento=date.today() + timedelta(days=30),
    )


def _crear_permisos():
    # Los tests no corren necesariamente la migracion de datos, asi que nos
    # aseguramos de tener los permisos del catalogo cargados.
    codigos = [
        VER_INVENTARIO, EDITAR_PRODUCTO, ELIMINAR_PRODUCTO,
        REGISTRAR_MOVIMIENTO,
    ]
    for codigo in codigos:
        Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'modulo': 'inventory', 'descripcion': codigo},
        )


def _crear_rol(tenant, nombre, permisos_codigos=()):
    rol = Rol.objects.create(tenant=tenant, nombre=nombre)
    if permisos_codigos:
        rol.permisos.add(*Permiso.objects.filter(codigo__in=permisos_codigos))
    return rol


def _crear_usuario(tenant, rol, email):
    user = Usuario(tenant=tenant, rol=rol, email=email)
    user.set_password('clave-segura-1234')
    user.save()
    return user


def _token(usuario):
    return str(RefreshToken.for_user(usuario).access_token)


class ProductoPermisosTests(APITestCase):
    """Permisos sobre /api/inventory/productos/."""

    @classmethod
    def setUpTestData(cls):
        _crear_permisos()

        cls.tenant = _crear_tenant('Tenant A')

        cls.rol_owner = _crear_rol(cls.tenant, 'Owner')  # bypass
        cls.rol_editor = _crear_rol(
            cls.tenant, 'Editor',
            permisos_codigos=[VER_INVENTARIO, EDITAR_PRODUCTO],
        )
        cls.rol_visor = _crear_rol(
            cls.tenant, 'Visor',
            permisos_codigos=[VER_INVENTARIO],
        )

        cls.owner  = _crear_usuario(cls.tenant, cls.rol_owner,  'owner@a.test')
        cls.editor = _crear_usuario(cls.tenant, cls.rol_editor, 'editor@a.test')
        cls.visor  = _crear_usuario(cls.tenant, cls.rol_visor,  'visor@a.test')

        cls.categoria = Categoria.objects.create(tenant=cls.tenant, nombre='General')
        cls.producto = Producto.objects.create(
            tenant=cls.tenant,
            categoria=cls.categoria,
            nombre='Producto X',
            unidad_medida='un',
            stock_actual=10,
            stock_minimo=2,
        )

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {_token(user)}')

    # ── 403: sin permiso ────────────────────────────────────────────────────

    def test_visor_sin_editar_producto_recibe_403_en_patch(self):
        """Criterio de aceptacion: sin 'editar_producto' -> 403 al modificar."""
        self._auth(self.visor)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.patch(url, {'nombre': 'Hackeado'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Producto X')

    def test_visor_sin_editar_producto_recibe_403_en_put(self):
        self._auth(self.visor)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.put(url, {
            'nombre': 'Otro',
            'unidad_medida': 'kg',
            'stock_actual': 0,
            'stock_minimo': 0,
            'categoria_id': str(self.categoria.id),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_visor_sin_editar_producto_recibe_403_en_create(self):
        self._auth(self.visor)
        url = reverse('producto-list')
        resp = self.client.post(url, {
            'nombre': 'Nuevo',
            'unidad_medida': 'un',
            'stock_actual': 1,
            'stock_minimo': 0,
            'categoria_id': str(self.categoria.id),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_visor_sin_eliminar_producto_recibe_403_en_destroy(self):
        self._auth(self.visor)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── 200: con el permiso ─────────────────────────────────────────────────

    def test_editor_con_editar_producto_puede_patch(self):
        self._auth(self.editor)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.patch(url, {'nombre': 'Renombrado'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Renombrado')

    def test_editor_no_puede_eliminar_sin_permiso(self):
        """El permiso eliminar_producto es independiente de editar_producto."""
        self._auth(self.editor)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_tiene_bypass(self):
        self._auth(self.owner)
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.patch(url, {'nombre': 'Owner-edit'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_visor_puede_listar(self):
        self._auth(self.visor)
        resp = self.client.get(reverse('producto-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_no_autenticado_recibe_401(self):
        self.client.credentials()  # sin token
        url = reverse('producto-detail', args=[self.producto.id])
        resp = self.client.patch(url, {'nombre': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TenantIsolationTests(APITestCase):
    """Aun con el permiso, no se puede tocar data de otro tenant."""

    @classmethod
    def setUpTestData(cls):
        _crear_permisos()
        cls.tenant_a = _crear_tenant('A')
        cls.tenant_b = _crear_tenant('B')

        cls.rol_editor_a = _crear_rol(
            cls.tenant_a, 'Editor',
            permisos_codigos=[VER_INVENTARIO, EDITAR_PRODUCTO],
        )
        cls.user_a = _crear_usuario(cls.tenant_a, cls.rol_editor_a, 'editor@a.test')

        categoria_b = Categoria.objects.create(tenant=cls.tenant_b, nombre='Cat B')
        cls.producto_b = Producto.objects.create(
            tenant=cls.tenant_b,
            categoria=categoria_b,
            nombre='Producto de B',
            unidad_medida='un',
            stock_actual=5,
            stock_minimo=0,
        )

    def test_editor_de_a_no_puede_editar_producto_de_b(self):
        """get_queryset filtra por tenant -> producto de B = 404, no 403."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {_token(self.user_a)}')
        url = reverse('producto-detail', args=[self.producto_b.id])
        resp = self.client.patch(url, {'nombre': 'Intento cruzado'}, format='json')
        self.assertIn(
            resp.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
        self.producto_b.refresh_from_db()
        self.assertEqual(self.producto_b.nombre, 'Producto de B')


class RolDeOtroTenantTests(APITestCase):
    """
    Defensa en profundidad: si un usuario quedara con un rol cuyo tenant
    no coincide (p.ej. por una corrupcion en la base), la autorizacion
    debe negarse aunque ese rol tenga el permiso.
    """

    @classmethod
    def setUpTestData(cls):
        _crear_permisos()
        cls.tenant_a = _crear_tenant('A')
        cls.tenant_b = _crear_tenant('B')

        # Rol del tenant B con todos los permisos
        cls.rol_b = _crear_rol(
            cls.tenant_b, 'Atacante',
            permisos_codigos=[EDITAR_PRODUCTO],
        )
        # Usuario del tenant A pero asignado al rol de B (escenario imposible
        # por la UI, pero queremos blindarlo).
        cls.user_a = Usuario(tenant=cls.tenant_a, rol=cls.rol_b, email='x@a.test')
        cls.user_a.set_password('clave-segura-1234')
        cls.user_a.save()

        categoria_a = Categoria.objects.create(tenant=cls.tenant_a, nombre='C')
        cls.producto_a = Producto.objects.create(
            tenant=cls.tenant_a,
            categoria=categoria_a,
            nombre='Producto A',
            unidad_medida='un',
            stock_actual=1,
            stock_minimo=0,
        )

    def test_rol_de_otro_tenant_es_rechazado(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {_token(self.user_a)}')
        url = reverse('producto-detail', args=[self.producto_a.id])
        resp = self.client.patch(url, {'nombre': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
