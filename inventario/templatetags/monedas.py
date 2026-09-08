from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un monto en pesos chilenos: sin decimales, con separador de
    miles, y el signo negativo antes del simbolo ($) en vez de despues.

    `${{ valor|floatformat:0 }}` se ve bien para montos positivos, pero para
    uno negativo concatena "$" + "-1.025.000" = "$-1.025.000", que no es
    como se escribe un monto negativo. Este filtro ya incluye el "$".
    """
    if valor is None:
        valor = 0
    negativo = valor < 0
    formateado = number_format(abs(valor), decimal_pos=0, force_grouping=True)
    return f"-${formateado}" if negativo else f"${formateado}"
