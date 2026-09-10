"""Formularios del modulo de Ingresos de inventario.

Son tres formularios independientes que se validan juntos en la vista:
cabecera del ingreso, datos del vehiculo y cantidades por pieza. Se separan
porque cada uno escribe en tablas distintas y porque el de cantidades no tiene
campos fijos (depende del catalogo).
"""

from django import forms
from django.utils import timezone

from ..models import Categoria, Entrada, normalizar_texto
from ..services import ImagenInvalidaError, validar_imagen

ANIO_MINIMO = 1900
CANTIDAD_MAXIMA = 9999
PREFIJO_CANTIDAD = "cantidad_"
PREFIJO_FOTO = "foto_"


def anio_maximo():
    """El proximo anio: los modelos nuevos se venden con anticipacion."""
    return timezone.localdate().year + 1


class EntradaForm(forms.ModelForm):
    class Meta:
        model = Entrada
        fields = ["fecha"]
        labels = {"fecha": "Fecha del ingreso"}
        widgets = {
            # `format` explicito: sin el, el locale es-CL renderiza
            # "06/09/2026" y un <input type="date"> descarta ese valor,
            # dejando el campo vacio al editar.
            "fecha": forms.DateInput(
                attrs={"type": "date", "class": "input-control"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate()

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha del ingreso no puede ser futura.")
        return fecha


class VehiculoIngresoForm(forms.Form):
    """Datos del vehiculo desarmado.

    Es un `Form` y no un `ModelForm` porque los tres textos alimentan tres
    tablas distintas (marca, modelo y tipo) que se crean o reutilizan en
    `servicios.ingresos.obtener_o_crear_vehiculo`. Todo se normaliza a
    mayusculas aqui ademas de en el modelo, para que el usuario vea el dato
    estandarizado si el formulario vuelve con errores.
    """

    marca = forms.CharField(
        max_length=50,
        label="Marca",
        widget=forms.TextInput(
            attrs={
                "class": "input-control",
                "list": "lista-marcas",
                "placeholder": "TOYOTA",
                "autocomplete": "off",
            }
        ),
    )
    modelo = forms.CharField(
        max_length=50,
        label="Modelo",
        widget=forms.TextInput(
            attrs={
                "class": "input-control",
                "list": "lista-modelos",
                "placeholder": "YARIS",
                "autocomplete": "off",
            }
        ),
    )
    # Lo opcional se marca en la etiqueta y los ejemplos van en el
    # placeholder: un help_text bajo el campo desalinea la fila de cinco
    # columnas, porque solo dos de los cinco lo tendrian.
    tipo_vehiculo = forms.CharField(
        max_length=50,
        required=False,
        label="Tipo de vehículo (opcional)",
        widget=forms.TextInput(
            attrs={
                "class": "input-control",
                "list": "lista-tipos",
                "placeholder": "SEDAN",
                "autocomplete": "off",
            }
        ),
    )
    anio_desde = forms.IntegerField(
        label="Año desde",
        widget=forms.NumberInput(
            attrs={"class": "input-control", "step": "1", "placeholder": "2014"}
        ),
    )
    anio_hasta = forms.IntegerField(
        label="Año hasta (opcional)",
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "input-control", "step": "1", "placeholder": "2018"}
        ),
    )

    def clean_marca(self):
        return normalizar_texto(self.cleaned_data["marca"])

    def clean_modelo(self):
        return normalizar_texto(self.cleaned_data["modelo"])

    def clean_tipo_vehiculo(self):
        return normalizar_texto(self.cleaned_data["tipo_vehiculo"])

    def _validar_anio(self, valor, campo):
        if valor is None:
            return
        if valor < ANIO_MINIMO or valor > anio_maximo():
            self.add_error(
                campo,
                f"El año debe estar entre {ANIO_MINIMO} y {anio_maximo()}.",
            )

    def clean(self):
        datos = super().clean()
        desde = datos.get("anio_desde")
        hasta = datos.get("anio_hasta")
        self._validar_anio(desde, "anio_desde")
        self._validar_anio(hasta, "anio_hasta")
        if desde and hasta and hasta < desde:
            self.add_error(
                "anio_hasta", "El año hasta no puede ser menor que el año desde."
            )
        return datos

    def datos_vehiculo(self):
        """Argumentos para `servicios.ingresos.obtener_o_crear_vehiculo`."""
        return {
            "marca": self.cleaned_data["marca"],
            "modelo": self.cleaned_data["modelo"],
            "tipo_vehiculo": self.cleaned_data["tipo_vehiculo"],
            "anio_desde": self.cleaned_data["anio_desde"],
            "anio_hasta": self.cleaned_data["anio_hasta"],
        }


class CategoriasIngresoForm(forms.Form):
    """Categorias marcadas. Solo decide que piezas se muestran, por eso no es
    obligatoria: lo que valida el ingreso son las cantidades."""

    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.order_by("nombre_categoria"),
        required=False,
        label="Categorías a ingresar",
        widget=forms.CheckboxSelectMultiple,
    )


class LineasIngresoForm(forms.Form):
    """Cantidad por pieza, leida de los inputs `cantidad_<idProducto>`.

    No se usa un `inlineformset` porque la pantalla lista cientos de piezas del
    catalogo de las que solo unas pocas llevan cantidad: el formset exigiria un
    subformulario y su management form para cada una.

    `piezas_permitidas` acota que ids acepta: sin esa lista bastaria con
    enviar un id cualquiera para inyectar stock en un producto ajeno al
    catalogo (IDOR).
    """

    def __init__(self, data=None, files=None, *, piezas_permitidas=(), **kwargs):
        super().__init__(data=data, files=files, **kwargs)
        self.piezas = {pieza.pk: pieza for pieza in piezas_permitidas}
        self.cantidades = {}
        self.lineas = []
        self.fotos = {}

    def clean(self):
        datos = super().clean()
        errores = []
        for clave in self.data:
            if not clave.startswith(PREFIJO_CANTIDAD):
                continue
            identificador = clave[len(PREFIJO_CANTIDAD) :]
            pieza = self.piezas.get(int(identificador)) if identificador.isdigit() else None
            if pieza is None:
                errores.append(
                    "Se recibió una pieza que no pertenece al catálogo mostrado."
                )
                continue
            texto = (self.data.get(clave) or "").strip()
            if not texto:
                continue
            try:
                cantidad = int(texto)
            except ValueError:
                errores.append(
                    f"La cantidad de «{pieza.nombre}» debe ser un número entero."
                )
                continue
            if cantidad < 0 or cantidad > CANTIDAD_MAXIMA:
                errores.append(
                    f"La cantidad de «{pieza.nombre}» debe estar entre 0 y "
                    f"{CANTIDAD_MAXIMA}."
                )
                continue
            self.cantidades[pieza.pk] = cantidad
            if cantidad > 0:
                self.lineas.append((pieza, cantidad))

        for clave in self.files:
            if not clave.startswith(PREFIJO_FOTO):
                continue
            identificador = clave[len(PREFIJO_FOTO) :]
            pieza = self.piezas.get(int(identificador)) if identificador.isdigit() else None
            if pieza is None:
                errores.append(
                    "Se recibió una foto de una pieza que no pertenece al catálogo mostrado."
                )
                continue
            archivo = self.files.get(clave)
            try:
                validar_imagen(archivo)
            except ImagenInvalidaError as exc:
                errores.append(f"La foto de «{pieza.nombre}»: {exc}")
                continue
            if self.cantidades.get(pieza.pk, 0) <= 0:
                # No se ignora en silencio: sin cantidad > 0 la pieza no entra
                # al ingreso y la foto se perderia sin que el operador sepa
                # por que (el input file no se puede "recordar" en el re-render).
                errores.append(
                    f"Pusiste una foto para «{pieza.nombre}» pero no indicaste "
                    "una cantidad mayor a 0: completala o sacá la foto."
                )
                continue
            self.fotos[pieza.pk] = archivo

        if not errores and not self.lineas:
            errores.append(
                "Indica una cantidad mayor a 0 en al menos una pieza."
            )
        if errores:
            # Se acumulan todos: asi el operador corrige de una sola vez.
            raise forms.ValidationError(errores)
        return datos
