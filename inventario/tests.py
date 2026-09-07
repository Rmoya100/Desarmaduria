from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import DetalleVentaFormSet
from .models import (
    Categoria,
    DetalleEntrada,
    Entrada,
    FormaPago,
    Producto,
    Rol,
    TipoDocumento,
    Usuario,
    Venta,
)
from .servicios.inventario import productos_con_stock


def crear_usuario(username, rol=None):
    return Usuario.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="clave-segura-123",
        nombre_usuario=username,
        rol=rol,
    )


def crear_producto_con_stock(cantidad, usuario, nombre="Producto de prueba"):
    categoria = Categoria.objects.create(nombre_categoria=f"Categoria {nombre}")
    producto = Producto.objects.create(categoria=categoria, nombre=nombre, costo=Decimal("1000"))
    entrada = Entrada.objects.create(fecha="2026-01-01", usuario=usuario)
    DetalleEntrada.objects.create(entrada=entrada, producto=producto, cantidad=cantidad)
    return producto


def datos_formset(prefix, lineas):
    """Arma el diccionario POST de un formset de Django (management form +
    una entrada por cada linea) a partir de una lista de dicts producto/
    cantidad/precio."""
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(lineas)),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for indice, linea in enumerate(lineas):
        for campo, valor in linea.items():
            data[f"{prefix}-{indice}-{campo}"] = valor
    return data


class DetalleVentaModelTests(TestCase):
    """DetalleVenta.clean() ya validaba stock antes de este modulo; se agrega
    cobertura porque no tenia pruebas."""

    def setUp(self):
        self.usuario = crear_usuario("usuario_stock")
        self.producto = crear_producto_con_stock(cantidad=5, usuario=self.usuario)
        self.venta = Venta.objects.create(
            fecha_venta="2026-01-02",
            tipo_documento=TipoDocumento.objects.create(tipo_documento="Boleta"),
            forma_pago=FormaPago.objects.create(forma_pago="Efectivo"),
            usuario=self.usuario,
        )

    def test_rechaza_cantidad_mayor_al_stock_disponible(self):
        detalle = self.venta.detalles.model(
            venta=self.venta, producto=self.producto, cantidad=100, precio=Decimal("500")
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    def test_acepta_cantidad_dentro_del_stock_disponible(self):
        detalle = self.venta.detalles.model(
            venta=self.venta, producto=self.producto, cantidad=5, precio=Decimal("500")
        )
        detalle.full_clean()  # no debe lanzar


class DetalleVentaFormSetTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("usuario_formset")
        self.producto = crear_producto_con_stock(cantidad=10, usuario=self.usuario)
        self.prefix = DetalleVentaFormSet(instance=Venta()).prefix

    def test_exige_al_menos_una_linea(self):
        data = datos_formset(self.prefix, [])
        formset = DetalleVentaFormSet(data, instance=Venta())
        self.assertFalse(formset.is_valid())

    def test_rechaza_producto_repetido_en_la_misma_venta(self):
        data = datos_formset(
            self.prefix,
            [
                {"producto": self.producto.pk, "cantidad": "1", "precio": "500"},
                {"producto": self.producto.pk, "cantidad": "1", "precio": "500"},
            ],
        )
        formset = DetalleVentaFormSet(data, instance=Venta())
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors())

    def test_acepta_lineas_de_productos_distintos(self):
        producto2 = crear_producto_con_stock(cantidad=10, usuario=self.usuario, nombre="Otro producto")
        data = datos_formset(
            self.prefix,
            [
                {"producto": self.producto.pk, "cantidad": "1", "precio": "500"},
                {"producto": producto2.pk, "cantidad": "1", "precio": "500"},
            ],
        )
        formset = DetalleVentaFormSet(data, instance=Venta())
        self.assertTrue(formset.is_valid(), formset.errors)


class VentaAccesoTests(TestCase):
    """El modulo 'ventas' se agrego al sistema de permisos por rol en la
    migracion 0006_seed_permisos_ventas; estas pruebas verifican que el
    control de acceso realmente funciona de punta a punta."""

    def setUp(self):
        self.rol_administrador = Rol.objects.get(nombre_rol="Administrador")
        self.usuario_autorizado = crear_usuario("con_permiso", rol=self.rol_administrador)
        self.rol_sin_permisos = Rol.objects.create(nombre_rol="RolSinPermisosTest")
        self.usuario_sin_permiso = crear_usuario("sin_permiso", rol=self.rol_sin_permisos)

    def test_usuario_anonimo_redirige_a_login(self):
        response = self.client.get(reverse("ventas"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_usuario_sin_permiso_recibe_403(self):
        self.client.force_login(self.usuario_sin_permiso)
        response = self.client.get(reverse("ventas"))
        self.assertEqual(response.status_code, 403)

    def test_usuario_autorizado_ve_la_lista(self):
        self.client.force_login(self.usuario_autorizado)
        response = self.client.get(reverse("ventas"))
        self.assertEqual(response.status_code, 200)


class VentaCrearViewTests(TestCase):
    def setUp(self):
        rol_administrador = Rol.objects.get(nombre_rol="Administrador")
        self.usuario = crear_usuario("vendedor", rol=rol_administrador)
        self.client.force_login(self.usuario)
        self.tipo_documento = TipoDocumento.objects.create(tipo_documento="Boleta")
        self.forma_pago = FormaPago.objects.create(forma_pago="Efectivo")
        self.producto = crear_producto_con_stock(cantidad=10, usuario=self.usuario)
        self.prefix = DetalleVentaFormSet(instance=Venta()).prefix

    def _post_data(self, lineas):
        data = {
            "fecha_venta": "2026-01-05",
            "tipo_documento": self.tipo_documento.pk,
            "forma_pago": self.forma_pago.pk,
        }
        data.update(datos_formset(self.prefix, lineas))
        return data

    def test_crear_venta_con_dos_lineas_descuenta_stock(self):
        producto2 = crear_producto_con_stock(cantidad=10, usuario=self.usuario, nombre="Filtro de aceite")
        data = self._post_data(
            [
                {"producto": self.producto.pk, "cantidad": "2", "precio": "1500"},
                {"producto": producto2.pk, "cantidad": "3", "precio": "800"},
            ]
        )
        response = self.client.post(reverse("venta_crear"), data)
        self.assertRedirects(response, reverse("venta_guardada"))
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(Venta.objects.get().detalles.count(), 2)
        stock_restante = productos_con_stock().get(pk=self.producto.pk).stock_disponible
        self.assertEqual(stock_restante, 8)

    def test_crear_venta_rechaza_stock_insuficiente(self):
        data = self._post_data(
            [{"producto": self.producto.pk, "cantidad": "999", "precio": "1500"}]
        )
        response = self.client.post(reverse("venta_crear"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)

    def test_crear_venta_rechaza_producto_duplicado(self):
        data = self._post_data(
            [
                {"producto": self.producto.pk, "cantidad": "1", "precio": "1500"},
                {"producto": self.producto.pk, "cantidad": "1", "precio": "1500"},
            ]
        )
        response = self.client.post(reverse("venta_crear"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)

    def test_crear_venta_sin_permiso_recibe_403(self):
        rol_sin_permisos = Rol.objects.create(nombre_rol="OtroRolSinPermisosTest")
        usuario_sin_permiso = crear_usuario("sin_permiso_crear", rol=rol_sin_permisos)
        self.client.force_login(usuario_sin_permiso)
        data = self._post_data(
            [{"producto": self.producto.pk, "cantidad": "1", "precio": "1500"}]
        )
        response = self.client.post(reverse("venta_crear"), data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Venta.objects.count(), 0)

    def test_venta_guardada_pregunta_por_nueva_venta(self):
        response = self.client.get(reverse("venta_guardada"))
        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode()
        self.assertIn(reverse("venta_crear"), contenido)
        self.assertIn(reverse("ventas"), contenido)


class VentaCicloCompletoTests(TestCase):
    """Cubre las vistas que no quedan ejercitadas por las pruebas de arriba:
    comprobante (HTML y PDF), edicion, eliminacion y exportacion del
    listado. El objetivo es detectar errores de plantilla o de vista, no
    solo de reglas de negocio."""

    def setUp(self):
        rol_administrador = Rol.objects.get(nombre_rol="Administrador")
        self.usuario = crear_usuario("ciclo_completo", rol=rol_administrador)
        self.client.force_login(self.usuario)
        self.producto = crear_producto_con_stock(cantidad=10, usuario=self.usuario)
        self.venta = Venta.objects.create(
            fecha_venta="2026-01-05",
            tipo_documento=TipoDocumento.objects.create(tipo_documento="Boleta"),
            forma_pago=FormaPago.objects.create(forma_pago="Efectivo"),
            usuario=self.usuario,
        )
        self.venta.detalles.create(producto=self.producto, cantidad=2, precio=Decimal("1500"))

    def test_comprobante_html(self):
        response = self.client.get(reverse("venta_comprobante", args=[self.venta.pk]))
        self.assertEqual(response.status_code, 200)

    def test_comprobante_pdf(self):
        response = self.client.get(reverse("venta_comprobante_pdf", args=[self.venta.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_editar_venta_get(self):
        response = self.client.get(reverse("venta_editar", args=[self.venta.pk]))
        self.assertEqual(response.status_code, 200)

    def test_eliminar_venta(self):
        response = self.client.get(reverse("venta_eliminar", args=[self.venta.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("venta_eliminar", args=[self.venta.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Venta.objects.filter(pk=self.venta.pk).exists())

    def test_exportar_pdf(self):
        response = self.client.get(reverse("ventas_exportar_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_exportar_excel(self):
        response = self.client.get(reverse("ventas_exportar_excel"))
        self.assertEqual(response.status_code, 200)


class SidebarSubmenuTests(TestCase):
    """El submenu de Inventario es un <details>, no un estado del servidor.

    Antes su visibilidad dependia de la clase `nav-group--active`, que Django
    aplicaba segun la URL actual: pulsar el padre navegaba a Inventario y el
    submenu quedaba abierto sin forma de cerrarlo. Estas pruebas fijan la
    estructura que permite alternarlo.
    """

    def setUp(self):
        self.usuario = crear_usuario("sidebar")
        self.usuario.is_superuser = True
        self.usuario.save()
        self.client.force_login(self.usuario)

    def _details(self, respuesta):
        html = respuesta.content.decode()
        inicio = html.index('<details class="nav-group"')
        return html[inicio:html.index(">", inicio) + 1]

    def test_el_grupo_es_un_details_desplegable(self):
        respuesta = self.client.get(reverse("dashboard"))
        html = respuesta.content.decode()
        self.assertIn('<details class="nav-group"', html)
        self.assertIn("<summary", html)
        # La clase antigua ya no debe decidir la visibilidad del submenu.
        self.assertNotIn("nav-group--active", html)
        self.assertEqual(html.count('class="nav-sublink'), 3)
        # Debe existir un unico <details>: si un comentario `{# #}` quedara
        # abierto, su texto se emitiria literal y el `<details>` que menciona
        # se parsearia como etiqueta real, dejando el menu dentro de un
        # desplegable cerrado e invisible.
        self.assertEqual(html.count("<details"), 1)

    def test_las_plantillas_no_emiten_comentarios_literales(self):
        """`{# ... #}` solo comenta una linea. Si se abre y no se cierra en la
        misma, Django lo trata como texto y lo escribe en el HTML."""
        for nombre in ["dashboard", "ventas", "gastos", "reportes"]:
            with self.subTest(vista=nombre):
                html = self.client.get(reverse(nombre)).content.decode()
                self.assertNotIn("{#", html)
                self.assertNotIn("{%", html)

    def test_abierto_solo_dentro_de_inventario(self):
        fuera = self._details(self.client.get(reverse("dashboard")))
        dentro = self._details(self.client.get(reverse("inventario_visualizacion")))
        self.assertNotIn("open", fuera)
        self.assertIn("open", dentro)
