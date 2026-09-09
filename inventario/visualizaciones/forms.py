from django import forms
from django.utils.html import format_html

from ..models import Categoria, Marca, Modelo, Producto, Vehiculo
from ..services import MAX_FOTOS_POR_PRODUCTO, ImagenInvalidaError, validar_imagen
from ..servicios.catalogo import PlanillaInvalidaError, leer_planilla

MAX_PLANILLA_BYTES = 5 * 1024 * 1024  # 5 MB
EXTENSIONES_PERMITIDAS = (".xlsx", ".xlsm")


class MultipleClearableFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Campo de subida de varios archivos a la vez.

    Django no trae esto de fabrica: `FileField.clean()` espera un unico
    archivo, asi que hay que envolverlo para que acepte la lista que llega
    de un `<input type="file" multiple>` (patron documentado por Django).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleClearableFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpiar_uno = super().clean
        if isinstance(data, (list, tuple)):
            return [limpiar_uno(archivo, initial) for archivo in data]
        return limpiar_uno(data, initial)


class CamaraOGaleriaWidget(MultipleClearableFileInput):
    """Dos disparadores para el mismo campo de fotos: uno abre la camara
    del dispositivo (atributo `capture`) y otro el selector de archivos/
    galeria comun. Los dos <input type="file"> comparten `name`, asi que
    el navegador los junta en la misma entrada de request.FILES (asi
    funciona multipart/form-data, no hace falta fusionar nada por JS);
    Django los entrega como lista porque hereda `allow_multiple_selected
    = True` de MultipleClearableFileInput.

    Los input se ubican por `data-foto-rol` dentro de un contenedor
    comun, no por `id`: `ProductoForm` se instancia sin `prefix` mas de
    una vez en la misma pagina (modal "Nuevo producto" + modal "Editar
    producto" cargado por fetch), asi que un id fijo colisionaria entre
    ambos formularios.
    """

    def id_for_label(self, id_):
        return None  # no hay un unico input al que asociar un <label for>

    def render(self, name, value, attrs=None, renderer=None):
        attrs = {**self.attrs, **(attrs or {})}
        max_fotos = attrs.get("data-max-fotos", "")
        return format_html(
            '<div class="foto-input" data-foto-input data-max-fotos="{max_fotos}">'
            '<input type="file" name="{name}" data-foto-rol="camara" class="visually-hidden" '
            'accept="image/*" capture="environment" tabindex="-1" aria-hidden="true">'
            '<input type="file" name="{name}" data-foto-rol="galeria" class="visually-hidden" '
            'accept="image/*,.heic,.heif" multiple tabindex="-1" aria-hidden="true">'
            '<div class="foto-input__botones">'
            '<button type="button" class="btn btn-sm" data-foto-abrir="camara">Tomar foto</button>'
            '<button type="button" class="btn btn-sm" data-foto-abrir="galeria">Elegir de galería</button>'
            '<button type="button" class="btn btn-sm" data-foto-quitar hidden>Quitar selección</button>'
            "</div>"
            '<p class="foto-input__resumen" data-foto-resumen aria-live="polite" hidden></p>'
            "</div>",
            max_fotos=max_fotos,
            name=name,
        )


class InventarioFiltroForm(forms.Form):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.order_by("nombre_categoria"),
        required=False,
        empty_label="Todas las categorías",
    )
    marca = forms.ModelChoiceField(
        queryset=Marca.objects.order_by("nombre_marca"),
        required=False,
        empty_label="Todas las marcas",
    )
    modelo = forms.ModelChoiceField(
        queryset=Modelo.objects.select_related("marca").order_by(
            "marca__nombre_marca", "nombre_modelo"
        ),
        required=False,
        empty_label="Todos los modelos",
    )
    estado = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Todos los estados"),
            ("disponible", "Con stock"),
            ("agotado", "Agotados"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "input-control"


class ProductoFiltroForm(forms.Form):
    nombre = forms.CharField(
        label="Buscar producto",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Nombre de la pieza"}
        ),
    )
    categoria = forms.CharField(
        label="Categoría",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Nombre de categoría"}
        ),
    )
    vehiculo = forms.CharField(
        label="Vehículo",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Marca, modelo o patente"}
        ),
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=(
            ("", "Plantillas y stock real"),
            ("plantilla", "Solo plantillas de catálogo"),
            ("stock", "Solo stock real (con vehículo)"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "input-control"
        # "tipo" filtra en el servidor (cambia el queryset), a diferencia de
        # nombre/categoria/vehiculo que se filtran en vivo por JS sin recargar:
        # se envia solo al cambiarlo, no hace falta un boton "Buscar" aparte.
        self.fields["tipo"].widget.attrs["onchange"] = "this.form.submit()"


class ProductoForm(forms.ModelForm):
    fotos = MultipleFileField(
        label="Fotos",
        required=False,
        widget=CamaraOGaleriaWidget(attrs={"data-max-fotos": MAX_FOTOS_POR_PRODUCTO}),
        help_text="Podés tomar una foto o elegir varias de la galería. La primera que subas queda como principal.",
    )

    class Meta:
        model = Producto
        fields = ["codigo", "nombre", "categoria", "vehiculo", "costo", "precio_venta"]
        labels = {
            "codigo": "Código",
            "nombre": "Nombre de la pieza",
            "categoria": "Categoría",
            "vehiculo": "Vehículo de origen",
            "costo": "Costo de adquisición",
            "precio_venta": "Precio de venta",
        }
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "input-control",
                    "placeholder": "Se genera solo si lo dejas vacío",
                }
            ),
            "nombre": forms.TextInput(attrs={"class": "input-control"}),
            "categoria": forms.Select(attrs={"class": "input-control"}),
            "vehiculo": forms.Select(attrs={"class": "input-control"}),
            "costo": forms.NumberInput(attrs={"class": "input-control", "min": "0", "step": "0.01"}),
            "precio_venta": forms.NumberInput(
                attrs={"class": "input-control", "min": "0", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["codigo"].required = False
        self.fields["vehiculo"].required = False
        self.fields["vehiculo"].empty_label = "Sin vehículo informado"
        self.fields["vehiculo"].help_text = (
            "Dejalo vacío para crear una plantilla reutilizable del catálogo. "
            "Si elegís un vehículo acá, la fila queda con 0 unidades de stock: "
            "para cargar stock real de una pieza que entró para un vehículo puntual, "
            "usá el módulo Ingresos — ahí se crea o reutiliza esta fila sola."
        )

    def clean_codigo(self):
        return self.cleaned_data.get("codigo") or None

    def clean_fotos(self):
        archivos = self.cleaned_data.get("fotos") or []
        if not isinstance(archivos, list):
            archivos = [archivos]
        existentes = self.instance.fotos.count() if self.instance.pk else 0
        if existentes + len(archivos) > MAX_FOTOS_POR_PRODUCTO:
            disponibles = max(MAX_FOTOS_POR_PRODUCTO - existentes, 0)
            raise forms.ValidationError(
                f"Este producto ya tiene {existentes} foto(s); podés agregar "
                f"{disponibles} más (máximo {MAX_FOTOS_POR_PRODUCTO})."
            )
        for archivo in archivos:
            try:
                validar_imagen(archivo)
            except ImagenInvalidaError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return archivos


class EdicionMasivaForm(forms.Form):

    filtro_categoria = forms.ModelChoiceField(
        label="Categoría",
        queryset=Categoria.objects.order_by("nombre_categoria"),
        required=False,
        empty_label="Todas las categorías",
    )
    filtro_marca = forms.ModelChoiceField(
        label="Marca",
        queryset=Marca.objects.order_by("nombre_marca"),
        required=False,
        empty_label="Todas las marcas",
    )
    filtro_modelo = forms.ModelChoiceField(
        label="Modelo",
        queryset=Modelo.objects.select_related("marca").order_by(
            "marca__nombre_marca", "nombre_modelo"
        ),
        required=False,
        empty_label="Todos los modelos",
    )
    filtro_vehiculo = forms.ModelChoiceField(
        label="Vehículo",
        queryset=Vehiculo.objects.select_related("modelo__marca").order_by(
            "modelo__marca__nombre_marca", "modelo__nombre_modelo", "anio_desde"
        ),
        required=False,
        empty_label="Todos los vehículos",
    )

    nueva_categoria = forms.ModelChoiceField(
        label="Nueva categoría",
        queryset=Categoria.objects.order_by("nombre_categoria"),
        required=False,
        empty_label="— sin cambio —",
    )
    nuevo_vehiculo = forms.ModelChoiceField(
        label="Nuevo vehículo",
        queryset=Vehiculo.objects.select_related("modelo__marca").order_by(
            "modelo__marca__nombre_marca", "modelo__nombre_modelo", "anio_desde"
        ),
        required=False,
        empty_label="— sin cambio —",
    )
    quitar_vehiculo = forms.BooleanField(
        label="Quitar el vehículo de los productos", required=False
    )
    nuevo_costo = forms.DecimalField(
        label="Fijar costo", required=False, min_value=0, decimal_places=2, max_digits=10
    )
    ajuste_costo_pct = forms.DecimalField(
        label="Ajustar costo (%)", required=False, decimal_places=2, max_digits=6,
        help_text="Ej: 10 sube 10 %, -5 baja 5 %.",
    )
    nuevo_precio_venta = forms.DecimalField(
        label="Fijar precio de venta", required=False, min_value=0,
        decimal_places=2, max_digits=10,
    )
    ajuste_precio_pct = forms.DecimalField(
        label="Ajustar precio de venta (%)", required=False,
        decimal_places=2, max_digits=6,
    )
    aplicar_a_todos = forms.BooleanField(
        label="Aplicar a todos los productos filtrados (ignorar selección)",
        required=False,
    )

    CAMPOS_CAMBIO = (
        "nueva_categoria",
        "nuevo_vehiculo",
        "quitar_vehiculo",
        "nuevo_costo",
        "ajuste_costo_pct",
        "nuevo_precio_venta",
        "ajuste_precio_pct",
    )

    def __init__(self, *args, exigir_cambios=True, **kwargs):
        self.exigir_cambios = exigir_cambios
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                continue
            campo.widget.attrs["class"] = "input-control"

    def clean(self):
        datos = super().clean()
        if datos.get("nuevo_vehiculo") and datos.get("quitar_vehiculo"):
            raise forms.ValidationError(
                "No puedes fijar un vehículo y quitarlo a la vez."
            )
        if datos.get("nuevo_costo") is not None and datos.get("ajuste_costo_pct") is not None:
            raise forms.ValidationError(
                "Elige fijar el costo o ajustarlo por %, no ambos."
            )
        if (
            datos.get("nuevo_precio_venta") is not None
            and datos.get("ajuste_precio_pct") is not None
        ):
            raise forms.ValidationError(
                "Elige fijar el precio de venta o ajustarlo por %, no ambos."
            )
        hay_cambio = any(
            datos.get(campo) not in (None, False, "") for campo in self.CAMPOS_CAMBIO
        )
        if self.exigir_cambios and not hay_cambio:
            raise forms.ValidationError("Indica al menos un cambio a aplicar.")
        return datos

    def filtrar(self, queryset):
        datos = self.cleaned_data
        if datos.get("filtro_categoria"):
            queryset = queryset.filter(categoria=datos["filtro_categoria"])
        if datos.get("filtro_marca"):
            queryset = queryset.filter(
                vehiculo__modelo__marca=datos["filtro_marca"]
            )
        if datos.get("filtro_modelo"):
            queryset = queryset.filter(vehiculo__modelo=datos["filtro_modelo"])
        if datos.get("filtro_vehiculo"):
            queryset = queryset.filter(vehiculo=datos["filtro_vehiculo"])
        return queryset


class ImportarCatalogoForm(forms.Form):
    """Sube la planilla y la interpreta en el mismo paso.

    La lectura ocurre aqui (no en la vista) para que un archivo ilegible sea
    un error de validacion normal del formulario, con su mensaje junto al
    campo. El resultado queda en `self.lectura`.
    """

    archivo = forms.FileField(
        label="Planilla Excel",
        help_text=(
            "Archivo .xlsx donde cada encabezado de columna es una categoría "
            "y las filas de abajo son las piezas."
        ),
        widget=forms.ClearableFileInput(
            attrs={"class": "input-control", "accept": ".xlsx,.xlsm"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lectura = None

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > MAX_PLANILLA_BYTES:
            raise forms.ValidationError("La planilla no puede superar los 5 MB.")
        if not archivo.name.lower().endswith(EXTENSIONES_PERMITIDAS):
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        try:
            # Se abre de verdad: la extension sola no garantiza el contenido.
            self.lectura = leer_planilla(archivo)
        except PlanillaInvalidaError as error:
            raise forms.ValidationError(str(error)) from error
        return archivo
