from django import forms

from .models import ConceptoGasto, FormaPago, Gasto, TipoDocumento
from .services import ImagenInvalidaError, validar_imagen


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
