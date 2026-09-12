from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    Categoria,
    ConceptoGasto,
    DetalleVenta,
    FormaPago,
    Gasto,
    Permiso,
    Producto,
    Rol,
    SaldoInicial,
    TipoDocumento,
    Usuario,
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
