from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from .models import (
    DetalleEntrada,
    Entrada,
    FormaPago,
    Marca,
    Modelo,
    Permiso,
    Producto,
    Rol,
    TipoDocumento,
    Usuario,
    Vehiculo,
)


class EstiloFormMixin:
    """Agrega la clase CSS `input-control` a los widgets de texto/select,
    para que todos los formularios del panel se vean consistentes sin tener
    que repetir `widgets={...}` en cada Form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                continue
            existente = widget.attrs.get("class", "")
            widget.attrs["class"] = (existente + " input-control").strip()


class LoginForm(EstiloFormMixin, AuthenticationForm):
    pass


class UsuarioForm(EstiloFormMixin, forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Déjalo en blanco para no cambiarla.",
    )

    class Meta:
        model = Usuario
        fields = ["username", "nombre_usuario", "email", "rol", "is_active", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields["password"].required = True
            self.fields["password"].help_text = ""

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
        return usuario


class RolForm(EstiloFormMixin, forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permiso.objects.order_by("modulo", "nombre_permiso"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Permisos",
    )

    class Meta:
        model = Rol
        fields = ["nombre_rol"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["permisos"].initial = Permiso.objects.filter(
                rol_permisos__rol=self.instance
            )

    def save(self, commit=True):
        rol = super().save(commit=commit)
        if commit:
            rol.rol_permisos.all().delete()
            for permiso in self.cleaned_data["permisos"]:
                rol.rol_permisos.create(permiso=permiso)
        return rol


class FormaPagoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = FormaPago
        fields = ["forma_pago"]


class TipoDocumentoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = TipoDocumento
        fields = ["tipo_documento"]


# ---------------------------------------------------------------------------
# Ingreso de stock (Entrada + líneas de DetalleEntrada)
#
# Los <select> de marca/modelo/vehículo/producto se encadenan en el cliente
# (inventario/entrada_form.js). Para que ese filtrado no dependa de llamadas
# AJAX, cada <option> lleva los ids de sus padres como atributos `data-*`,
# que estos widgets inyectan al renderizar.
# ---------------------------------------------------------------------------
class _DataAttrSelect(forms.Select):
    """Select que copia datos de cada instancia a su <option> como `data-*`.

    `data_attrs` es {nombre_atributo: campo_o_callable}. `campo` se lee con
    getattr; `callable` recibe la instancia y devuelve el valor.
    """

    data_attrs: dict = {}

    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        value = option["value"]
        instancia = getattr(value, "instance", None)
        if instancia is not None:
            for attr, fuente in self.data_attrs.items():
                dato = fuente(instancia) if callable(fuente) else getattr(instancia, fuente)
                option["attrs"][f"data-{attr}"] = dato
        return option


class ModeloSelect(_DataAttrSelect):
    data_attrs = {"marca": "marca_id"}


class VehiculoSelect(_DataAttrSelect):
    data_attrs = {"marca": lambda v: v.modelo.marca_id, "modelo": "modelo_id"}


class ProductoSelect(_DataAttrSelect):
    data_attrs = {"vehiculo": "vehiculo_id", "modelo": lambda p: p.vehiculo.modelo_id}


class EntradaForm(EstiloFormMixin, forms.ModelForm):
    marca = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Marca",
        help_text="Filtra los modelos disponibles.",
    )
    modelo = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Modelo",
        widget=ModeloSelect,
        help_text="Filtra los vehículos disponibles.",
    )

    class Meta:
        model = Entrada
        fields = ["fecha", "marca", "modelo", "vehiculo", "tipo_documento"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "vehiculo": VehiculoSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["marca"].queryset = Marca.objects.order_by("nombre_marca")
        self.fields["modelo"].queryset = (
            Modelo.objects.select_related("marca").order_by(
                "marca__nombre_marca", "nombre_modelo"
            )
        )
        self.fields["vehiculo"].queryset = (
            Vehiculo.objects.select_related("modelo__marca").order_by(
                "modelo__marca__nombre_marca", "modelo__nombre_modelo", "anio"
            )
        )
        self.fields["vehiculo"].label_from_instance = lambda v: (
            f"{v.modelo} {v.anio}" + (f" · {v.patente}" if v.patente else "")
        )
        if not self.is_bound:
            self.fields["fecha"].initial = timezone.localdate()


class DetalleEntradaForm(EstiloFormMixin, forms.ModelForm):
    cantidad = forms.IntegerField(min_value=1, label="Cantidad")

    class Meta:
        model = DetalleEntrada
        fields = ["producto", "cantidad"]
        widgets = {"producto": ProductoSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = (
            Producto.objects.select_related("vehiculo").order_by("nombre")
        )
        self.fields["producto"].label_from_instance = lambda p: p.nombre


DetalleEntradaFormSet = forms.inlineformset_factory(
    Entrada,
    DetalleEntrada,
    form=DetalleEntradaForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
