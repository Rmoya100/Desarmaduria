from datetime import date

from django import forms

from ..models import Producto

# Vehiculo.anio es PositiveSmallIntegerField; no tiene sentido aceptar años
# futuros mas alla del proximo (modelos que se adelantan).
ANIO_MAX = date.today().year + 1


class IngresoCabeceraForm(forms.Form):
    """Paso 1: fecha del ingreso y vehiculo del que se desarma. El vehiculo se
    guarda en Entrada.vehiculo y se asigna a todas las piezas del ingreso."""

    fecha = forms.DateField(
        label="Fecha del ingreso",
        widget=forms.DateInput(attrs={"type": "date", "class": "input-control"}),
    )
    marca = forms.CharField(
        label="Marca", max_length=50,
        widget=forms.TextInput(attrs={"class": "input-control", "placeholder": "Marca"}),
    )
    modelo = forms.CharField(
        label="Modelo", max_length=50,
        widget=forms.TextInput(attrs={"class": "input-control", "placeholder": "Modelo"}),
    )
    anio = forms.IntegerField(
        label="Año", min_value=1900, max_value=ANIO_MAX,
        widget=forms.NumberInput(attrs={"class": "input-control", "placeholder": "Año"}),
    )
    tipo = forms.CharField(
        label="Tipo de vehículo", required=False, max_length=50,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Automóvil, camioneta, SUV…"}
        ),
    )


class IngresoLineaForm(forms.Form):
    """Una fila de la tabla del paso 2: un producto ya existente al que se le
    informa la cantidad recibida y, opcionalmente, se le corrige costo y
    precio de venta. El vehiculo viene del paso 1 (es el mismo para todo el
    ingreso)."""

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(), widget=forms.HiddenInput()
    )
    cantidad = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": "input-control", "min": "1", "placeholder": "0"}
        ),
    )
    costo = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "input-control", "min": "0", "step": "0.01"}
        ),
    )
    precio_venta = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "input-control", "min": "0", "step": "0.01"}
        ),
    )

    CAMPOS_PRODUCTO = ("costo", "precio_venta")
    # Se muestran vacios con el valor actual como placeholder: asi una fila que
    # el usuario no toco queda realmente vacia (no se envia) y dejar el campo
    # en blanco significa "no cambiar".
    CAMPOS_VALOR_ACTUAL = ("costo", "precio_venta")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.CAMPOS_VALOR_ACTUAL:
            actual = self.initial.pop(campo, None)
            if actual not in (None, ""):
                self.fields[campo].widget.attrs["placeholder"] = str(actual)

    def clean(self):
        datos = super().clean()
        hay_datos_producto = any(
            datos.get(campo) not in (None, "") for campo in self.CAMPOS_PRODUCTO
        )
        if hay_datos_producto and not datos.get("cantidad"):
            raise forms.ValidationError(
                "Indica la cantidad recibida para guardar los datos de esta fila."
            )
        return datos
