import io
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import DetalleVentaFormSet
from .visualizaciones.forms import ProductoForm
from .models import (
    Categoria,
    DetalleEntrada,
    Entrada,
    FormaPago,
    Marca,
    Modelo,
    Producto,
    ProductoFoto,
    Rol,
    TipoDocumento,
    Usuario,
    Vehiculo,
    Venta,
)
from .servicios.ingresos import obtener_o_crear_vehiculo, resolver_producto
from .servicios.inventario import productos_con_stock
from .services import MAX_FOTOS_POR_PRODUCTO
from .views import _productos_json


def imagen_prueba(nombre="foto.png", color=(255, 0, 0)):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), color).save(buffer, format="PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


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


class ProductoDescripcionCompletaTests(TestCase):
    """`Producto.descripcion_completa` (y por lo tanto `__str__`) debe
    incluir el vehiculo cuando el producto es stock real de un vehiculo
    puntual, para no confundir en Ventas productos con el mismo nombre que
    pertenecen a vehiculos distintos."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre_categoria="Motor")

    def test_plantilla_sin_vehiculo_muestra_solo_el_nombre(self):
        plantilla = Producto.objects.create(categoria=self.categoria, nombre="Alternador")
        self.assertEqual(plantilla.descripcion_completa, "ALTERNADOR")
        self.assertEqual(str(plantilla), "ALTERNADOR")

    def test_producto_con_vehiculo_incluye_marca_modelo_anio(self):
        vehiculo = Vehiculo.objects.create(
            modelo=Modelo.objects.create(
                marca=Marca.objects.create(nombre_marca="TOYOTA"), nombre_modelo="YARIS"
            ),
            anio_desde=2008,
        )
        real = Producto.objects.create(
            categoria=self.categoria, nombre="Alternador", vehiculo=vehiculo
        )
        self.assertIn("TOYOTA YARIS 2008", real.descripcion_completa)
        self.assertIn("ALTERNADOR", real.descripcion_completa)
        self.assertEqual(str(real), real.descripcion_completa)


class ProductosJsonVentaTests(TestCase):
    """El catalogo que alimenta el buscador de productos del formulario de
    Ventas debe traer el vehiculo, para distinguir productos con el mismo
    nombre que pertenecen a vehiculos distintos (ver `static/js/inventario.js`,
    `renderizarListaModal`)."""

    def test_incluye_vehiculo_para_distinguir_productos_repetidos(self):
        categoria = Categoria.objects.create(nombre_categoria="Motor")
        vehiculo = Vehiculo.objects.create(
            modelo=Modelo.objects.create(
                marca=Marca.objects.create(nombre_marca="SUZUKI"), nombre_modelo="SX4"
            ),
            anio_desde=2007,
            anio_hasta=2012,
        )
        Producto.objects.create(categoria=categoria, nombre="Alternador", vehiculo=vehiculo)
        Producto.objects.create(categoria=categoria, nombre="Alternador")  # plantilla

        datos = _productos_json()
        con_vehiculo = [d for d in datos if d["nombre"] == "ALTERNADOR" and d["vehiculo"]]
        sin_vehiculo = [d for d in datos if d["nombre"] == "ALTERNADOR" and not d["vehiculo"]]
        self.assertEqual(len(con_vehiculo), 1)
        self.assertEqual(len(sin_vehiculo), 1)
        self.assertIn("SUZUKI SX4", con_vehiculo[0]["vehiculo"])


class VentaComprobanteVehiculoTests(TestCase):
    """El comprobante de venta debe mostrar el vehiculo del producto, no
    solo su nombre, ahora que `Producto.__str__` incluye la descripcion
    completa."""

    def setUp(self):
        self.usuario = crear_usuario("comprobante_vehiculo")
        self.usuario.is_superuser = True
        self.usuario.save()
        self.client.force_login(self.usuario)
        categoria = Categoria.objects.create(nombre_categoria="Motor")
        vehiculo = Vehiculo.objects.create(
            modelo=Modelo.objects.create(
                marca=Marca.objects.create(nombre_marca="TOYOTA"), nombre_modelo="YARIS"
            ),
            anio_desde=2008,
        )
        self.producto = Producto.objects.create(
            categoria=categoria, nombre="Alternador", vehiculo=vehiculo, costo=Decimal("1000")
        )
        entrada = Entrada.objects.create(fecha="2026-01-01", usuario=self.usuario)
        DetalleEntrada.objects.create(entrada=entrada, producto=self.producto, cantidad=5)
        self.venta = Venta.objects.create(
            fecha_venta="2026-01-05",
            tipo_documento=TipoDocumento.objects.create(tipo_documento="Boleta"),
            forma_pago=FormaPago.objects.create(forma_pago="Efectivo"),
            usuario=self.usuario,
        )
        self.venta.detalles.create(producto=self.producto, cantidad=2, precio=Decimal("1500"))

    def test_comprobante_html_muestra_vehiculo_del_producto(self):
        respuesta = self.client.get(reverse("venta_comprobante", args=[self.venta.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "TOYOTA YARIS 2008")

    def test_comprobante_pdf_se_genera_sin_errores(self):
        respuesta = self.client.get(reverse("venta_comprobante_pdf", args=[self.venta.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")


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
        # El sidebar tiene dos grupos desplegables: Inventario (Existencias,
        # Inventario valorizado) y Productos (Listado, Edicion masiva,
        # Importar). Si un comentario `{# #}` quedara abierto apareceria un
        # <details> de mas o de menos.
        self.assertEqual(html.count("<details"), 2)
        self.assertEqual(html.count('class="nav-sublink'), 5)

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


class ProductoGaleriaTests(TestCase):
    """Cobertura de la galeria de fotos (docs/analisis_fotos_productos.md):
    varias fotos por producto, una unica principal, reordenar y promocion
    automatica de la principal al eliminarla."""

    def setUp(self):
        self.usuario = crear_usuario("galeria")
        self.usuario.is_superuser = True
        self.usuario.save()
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.create(nombre_categoria="Motor")
        self.producto = Producto.objects.create(categoria=self.categoria, nombre="Alternador")

    def _datos_base(self, **extra):
        datos = {
            "codigo": self.producto.codigo or "",
            "nombre": self.producto.nombre,
            "categoria": self.categoria.pk,
            "vehiculo": "",
            "costo": "",
            "precio_venta": "",
        }
        datos.update(extra)
        return datos

    def test_subir_varias_fotos_marca_la_primera_como_principal(self):
        respuesta = self.client.post(
            reverse("producto_editar", args=[self.producto.pk]),
            data=self._datos_base(fotos=[imagen_prueba("a.png"), imagen_prueba("b.png")]),
        )
        self.assertEqual(respuesta.status_code, 302)
        fotos = list(self.producto.fotos.order_by("orden", "id_foto"))
        self.assertEqual(len(fotos), 2)
        self.assertTrue(fotos[0].es_principal)
        self.assertFalse(fotos[1].es_principal)
        self.assertTrue(fotos[0].imagen.name.endswith(".webp"))

    def test_no_permite_mas_del_maximo_de_fotos(self):
        respuesta = self.client.post(
            reverse("producto_editar", args=[self.producto.pk]),
            data=self._datos_base(fotos=[imagen_prueba(f"{i}.png") for i in range(9)]),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("fotos", respuesta.context["form"].errors)
        self.assertEqual(self.producto.fotos.count(), 0)

    def test_marcar_principal_desmarca_las_demas(self):
        foto_1 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("a.png"))
        foto_2 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("b.png"))
        self.assertTrue(foto_1.es_principal)

        respuesta = self.client.post(
            reverse("producto_foto_principal", args=[self.producto.pk, foto_2.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        foto_1.refresh_from_db()
        foto_2.refresh_from_db()
        self.assertFalse(foto_1.es_principal)
        self.assertTrue(foto_2.es_principal)

    def test_eliminar_la_principal_promueve_la_siguiente(self):
        foto_1 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("a.png"))
        foto_2 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("b.png"))

        respuesta = self.client.post(
            reverse("producto_foto_eliminar", args=[self.producto.pk, foto_1.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(ProductoFoto.objects.filter(pk=foto_1.pk).exists())
        foto_2.refresh_from_db()
        self.assertTrue(foto_2.es_principal)

    def test_mover_reordena_las_fotos(self):
        foto_1 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("a.png"))
        foto_2 = ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("b.png"))

        respuesta = self.client.post(
            reverse("producto_foto_mover", args=[self.producto.pk, foto_2.pk]),
            data={"direccion": "arriba"},
        )
        self.assertEqual(respuesta.status_code, 302)
        orden = list(
            self.producto.fotos.order_by("orden", "id_foto").values_list("pk", flat=True)
        )
        self.assertEqual(orden, [foto_2.pk, foto_1.pk])

    def test_listado_de_productos_usa_la_foto_principal(self):
        ProductoFoto.objects.create(producto=self.producto, imagen=imagen_prueba("a.png"))
        respuesta = self.client.get(reverse("productos_lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "thumbnail")

    def test_widget_renderiza_boton_camara_y_boton_galeria(self):
        """El campo `fotos` debe ofrecer, sobre todo en movil, un disparador
        que abre la camara del dispositivo y otro que abre la galeria/
        explorador de archivos, ambos alimentando el mismo campo."""
        html = ProductoForm().as_p()
        self.assertEqual(html.count('capture="environment"'), 1)
        self.assertIn('data-foto-rol="camara"', html)
        self.assertIn('data-foto-rol="galeria"', html)
        self.assertIn("Tomar foto", html)
        self.assertIn("Elegir de galería", html)

        entrada_camara = re.search(r'<input[^>]*data-foto-rol="camara"[^>]*>', html).group()
        entrada_galeria = re.search(r'<input[^>]*data-foto-rol="galeria"[^>]*>', html).group()
        # El input de camara no debe permitir seleccion multiple (una foto
        # por toque); el de galeria si, para elegir varias de una.
        self.assertNotIn("multiple", entrada_camara)
        self.assertIn("multiple", entrada_galeria)
        self.assertIn('name="fotos"', entrada_camara)
        self.assertIn('name="fotos"', entrada_galeria)

    def test_widget_no_genera_label_for_colgante(self):
        """Ya no hay un unico <input> al que apuntar: el <label> del campo
        no debe llevar un `for` que no exista en el HTML."""
        widget = ProductoForm().fields["fotos"].widget
        self.assertIsNone(widget.id_for_label("id_fotos"))

    def test_subir_fotos_de_camara_y_galeria_combinadas(self):
        """Simula lo que arma un navegador real: dos <input type="file">
        con el mismo `name="fotos"` (uno de la camara, otro de la galeria)
        llegan juntos en una sola lista via request.FILES.getlist."""
        respuesta = self.client.post(
            reverse("producto_editar", args=[self.producto.pk]),
            data=self._datos_base(
                fotos=[
                    imagen_prueba("camara.png"),
                    imagen_prueba("galeria1.png"),
                    imagen_prueba("galeria2.png"),
                ]
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.producto.fotos.count(), 3)


class IngresoFotoTests(TestCase):
    """La foto por linea de Ingresos debe terminar en el producto REAL del
    vehiculo (nunca en la plantilla), respetar MAX_FOTOS_POR_PRODUCTO y
    rechazar ids fuera de piezas_permitidas igual que ya se rechaza
    `cantidad_<id>` (proteccion anti-IDOR)."""

    def setUp(self):
        self.usuario = crear_usuario("ingresos")
        self.usuario.is_superuser = True
        self.usuario.save()
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.create(nombre_categoria="Motor")
        self.plantilla = Producto.objects.create(categoria=self.categoria, nombre="Alternador")

    def _datos(self, cantidad_pk, cantidad, foto_pk=None, foto=None):
        datos = {
            "fecha": "2026-09-08",
            f"cantidad_{cantidad_pk}": str(cantidad),
            "marca": "SUZUKI",
            "modelo": "SX4",
            "tipo_vehiculo": "",
            "anio_desde": "2007",
            "anio_hasta": "2012",
        }
        if foto is not None:
            datos[f"foto_{foto_pk}"] = foto
        return datos

    def test_foto_termina_en_producto_real_no_en_la_plantilla(self):
        respuesta = self.client.post(
            reverse("ingreso_crear"),
            data=self._datos(self.plantilla.pk, 3, self.plantilla.pk, imagen_prueba("a.png")),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.plantilla.refresh_from_db()
        self.assertEqual(self.plantilla.fotos.count(), 0)
        real = Producto.objects.get(nombre="ALTERNADOR", vehiculo__isnull=False)
        self.assertEqual(real.fotos.count(), 1)

    def test_respeta_el_maximo_de_fotos(self):
        vehiculo = obtener_o_crear_vehiculo(
            marca="SUZUKI", modelo="SX4", tipo_vehiculo="", anio_desde=2007, anio_hasta=2012
        )
        real = resolver_producto(self.plantilla, vehiculo)
        for i in range(MAX_FOTOS_POR_PRODUCTO):
            ProductoFoto.objects.create(producto=real, imagen=imagen_prueba(f"{i}.png"))

        respuesta = self.client.post(
            reverse("ingreso_crear"),
            data=self._datos(self.plantilla.pk, 1, self.plantilla.pk, imagen_prueba("extra.png")),
            follow=True,
        )
        self.assertEqual(respuesta.status_code, 200)
        real.refresh_from_db()
        self.assertEqual(real.fotos.count(), MAX_FOTOS_POR_PRODUCTO)
        mensajes = [str(m) for m in respuesta.context["messages"]]
        self.assertTrue(any("no se guardó" in m for m in mensajes))

    def test_foto_de_pieza_no_permitida_se_rechaza_como_el_idor_de_cantidad(self):
        otro_vehiculo = Vehiculo.objects.create(
            modelo=Modelo.objects.create(
                marca=Marca.objects.create(nombre_marca="TOYOTA"), nombre_modelo="YARIS"
            ),
            anio_desde=2008,
        )
        ajeno = Producto.objects.create(
            categoria=self.categoria, nombre="Alternador", vehiculo=otro_vehiculo
        )
        respuesta = self.client.post(
            reverse("ingreso_crear"),
            data=self._datos(self.plantilla.pk, 1, ajeno.pk, imagen_prueba("intento.png")),
        )
        self.assertEqual(respuesta.status_code, 200)
        errores = " ".join(respuesta.context["form_lineas"].non_field_errors())
        self.assertIn("no pertenece al catálogo mostrado", errores)
        self.assertEqual(ajeno.fotos.count(), 0)

    def test_foto_sin_cantidad_muestra_aviso_en_vez_de_ignorarla(self):
        respuesta = self.client.post(
            reverse("ingreso_crear"),
            data=self._datos(self.plantilla.pk, 0, self.plantilla.pk, imagen_prueba("huerfana.png")),
        )
        self.assertEqual(respuesta.status_code, 200)
        errores = " ".join(respuesta.context["form_lineas"].non_field_errors())
        self.assertIn("no indicaste", errores)
