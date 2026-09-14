from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from .models import (
    Categoria,
    ConceptoGasto,
    DetalleEntrada,
    DetalleVenta,
    Entrada,
    FormaPago,
    Gasto,
    Marca,
    Modelo,
    Permiso,
    Producto,
    Rol,
    SaldoInicial,
    TipoDocumento,
    Usuario,
    Vehiculo,
    Venta,
)
from .services import ImagenInvalidaError, validar_imagen


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


class GastoForm(forms.ModelForm):
    concepto = forms.ModelChoiceField(
        queryset=ConceptoGasto.objects.order_by("nombre_gasto"),
        empty_label="Selecciona el concepto",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    forma_pago = forms.ModelChoiceField(
        queryset=FormaPago.objects.order_by("forma_pago"),
        empty_label="Selecciona la forma de pago",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.order_by("tipo_documento"),
        required=False,
        empty_label="Selecciona el tipo de documento",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Gasto
        fields = [
            "concepto",
            "forma_pago",
            "fecha",
            "monto",
            "tipo_documento",
            "numero_documento",
            "observaciones",
            "imagen",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "monto": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "numero_documento": forms.TextInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "imagen": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        # Un archivo recien subido tiene content_type; el FieldFile de una
        # imagen ya guardada (cuando se edita sin tocar este campo) no lo
        # tiene, asi que esto valida solo cuando llega un archivo nuevo.
        if imagen and hasattr(imagen, "content_type"):
            try:
                validar_imagen(imagen)
            except ImagenInvalidaError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return imagen


class ConceptoGastoForm(forms.ModelForm):
    class Meta:
        model = ConceptoGasto
        fields = ["nombre_gasto"]
        widgets = {
            "nombre_gasto": forms.TextInput(attrs={"class": "form-control"}),
        }


class SaldoInicialForm(forms.ModelForm):
    class Meta:
        model = SaldoInicial
        fields = ["monto", "fecha", "observaciones"]
        widgets = {
            "monto": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }


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


class CategoriaForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre_categoria"]


class VentaForm(EstiloFormMixin, forms.ModelForm):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.order_by("tipo_documento"),
        empty_label="Selecciona el tipo de documento",
    )
    forma_pago = forms.ModelChoiceField(
        queryset=FormaPago.objects.order_by("forma_pago"),
        empty_label="Selecciona la forma de pago",
    )

    class Meta:
        model = Venta
        fields = ["fecha_venta", "tipo_documento", "forma_pago", "observaciones"]
        widgets = {
            "fecha_venta": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }


class DetalleVentaForm(EstiloFormMixin, forms.ModelForm):
    # Los 3 campos son HiddenInput: la linea completa (producto, cantidad y
    # precio) se carga desde el modal "Buscar producto" de inventario.js, no
    # escribiendo directo en la tabla. La validacion de backend (producto
    # valido y no eliminado, cantidad/precio requeridos) no cambia en nada.
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(fecha_eliminacion__isnull=True).order_by("nombre"),
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad", "precio"]
        widgets = {
            "cantidad": forms.HiddenInput(),
            "precio": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get("producto")
        if producto and self.instance.pk is None:
            # Solo de referencia: el precio REAL de venta (`precio`) lo sigue
            # tipeando el vendedor sin ningun cambio. Esto congela cuanto se
            # estimaba vender el producto en el momento de esta venta, para
            # poder compararlo despues aunque el precio_venta del producto
            # cambie mas adelante. No esta en Meta.fields, asi que
            # construct_instance() no lo pisa despues.
            self.instance.precio_estimado = producto.precio_venta
        return cleaned_data


class BaseDetalleVentaFormSet(forms.BaseInlineFormSet):
    """Ademas de las validaciones normales del formset, no deja repetir un
    mismo producto en dos lineas de la misma venta: cada linea valida el
    stock disponible por separado (ver DetalleVenta.clean), asi que dos
    lineas del mismo producto podrian aprobar en conjunto mas stock del que
    realmente existe.

    El "al menos una linea" se valida aqui a mano (en vez de con
    min_num/validate_min en la factory) porque min_num tambien hace que
    Django pre-renderice una fila vacia cuando la venta todavia no tiene
    ninguna linea; como los campos de cada fila son HiddenInput y solo se
    llenan via el modal "Buscar producto" (inventario.js), esa fila vacia
    quedaba sin producto y bloqueaba el guardado hasta que el usuario la
    quitaba a mano."""

    def clean(self):
        super().clean()
        productos_vistos = set()
        lineas_validas = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            producto = form.cleaned_data.get("producto")
            if not producto:
                continue
            lineas_validas += 1
            if producto.pk in productos_vistos:
                raise forms.ValidationError(
                    "Un producto no puede repetirse en la misma venta."
                )
            productos_vistos.add(producto.pk)
        if lineas_validas == 0:
            raise forms.ValidationError("Agrega al menos un producto a la venta.")


DetalleVentaFormSet = forms.inlineformset_factory(
    Venta,
    DetalleVenta,
    form=DetalleVentaForm,
    formset=BaseDetalleVentaFormSet,
    fields=["producto", "cantidad", "precio"],
    extra=0,
    can_delete=True,
)
