from datetime import date

from django import forms

from ..models import Producto

# Vehiculo.anio es PositiveSmallIntegerField; no tiene sentido aceptar años
# futuros mas alla del proximo (modelos que se adelantan).
ANIO_MAX = date.today().year + 1


class IngresoCabeceraForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha del ingreso",
        widget=forms.DateInput(attrs={"type": "date", "class": "input-control"}),
    )


class IngresoLineaForm(forms.Form):
    """Una fila de la pantalla de ingresos: un producto ya existente al que se
    le informa la cantidad recibida y, opcionalmente, se le corrige costo,
    precio de venta y vehiculo de origen (marca + modelo + año, que se crean
    en sus tablas si no existen)."""

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
    marca = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Marca"}
        ),
    )
    modelo = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "input-control", "placeholder": "Modelo"}
        ),
    )
    anio = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=ANIO_MAX,
        widget=forms.NumberInput(
            attrs={"class": "input-control", "placeholder": "Año"}
        ),
    )

    CAMPOS_VEHICULO = ("marca", "modelo", "anio")
    CAMPOS_PRODUCTO = ("costo", "precio_venta", "marca", "modelo", "anio")

    def clean(self):
        datos = super().clean()

        informados = [
            datos.get(campo) not in (None, "") for campo in self.CAMPOS_VEHICULO
        ]
        if any(informados) and not all(informados):
            raise forms.ValidationError(
                "Para asignar un vehículo completa marca, modelo y año."
            )

        # Costo/precio/vehiculo se guardan sobre el Producto al registrar el
        # ingreso; sin cantidad no hay ingreso, asi que esos datos se ignorarian.
        hay_datos_producto = any(
            datos.get(campo) not in (None, "") for campo in self.CAMPOS_PRODUCTO
        )
        if hay_datos_producto and not datos.get("cantidad"):
            raise forms.ValidationError(
                "Indica la cantidad recibida para guardar los datos de esta fila."
            )
        return datos
