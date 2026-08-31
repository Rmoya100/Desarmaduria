from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import FormaPago, Permiso, Rol, TipoDocumento, Usuario


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
