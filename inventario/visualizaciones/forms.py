from django import forms

from ..models import Categoria, Marca, Modelo, Producto, Vehiculo
from ..servicios.catalogo import PlanillaInvalidaError, leer_planilla

MAX_PLANILLA_BYTES = 5 * 1024 * 1024  # 5 MB
EXTENSIONES_PERMITIDAS = (".xlsx", ".xlsm")


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "input-control"


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "vehiculo", "costo"]
        labels = {
            "nombre": "Nombre de la pieza",
            "categoria": "Categoría",
            "vehiculo": "Vehículo de origen",
            "costo": "Costo de adquisición",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "input-control"}),
            "categoria": forms.Select(attrs={"class": "input-control"}),
            "vehiculo": forms.Select(attrs={"class": "input-control"}),
            "costo": forms.NumberInput(attrs={"class": "input-control", "min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehiculo"].required = False
        self.fields["vehiculo"].empty_label = "Sin vehículo informado"


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