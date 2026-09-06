from django import forms

from ..models import Categoria, Marca, Modelo, Producto, Vehiculo


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

    def clean_codigo(self):
        return self.cleaned_data.get("codigo") or None


class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel (.xlsx)",
        widget=forms.ClearableFileInput(
            attrs={"class": "input-control", "accept": ".xlsx"}
        ),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("El archivo debe tener extensión .xlsx.")
        return archivo


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
            "modelo__marca__nombre_marca", "modelo__nombre_modelo", "anio"
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
            "modelo__marca__nombre_marca", "modelo__nombre_modelo", "anio"
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
