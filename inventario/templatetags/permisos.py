from django import template

from inventario.permisos import tiene_permiso as _tiene_permiso

register = template.Library()


@register.filter
def tiene_permiso(user, modulo_accion):
    """Uso en template: {% if request.user|tiene_permiso:"usuarios:ver" %}"""
    modulo, _, accion = modulo_accion.partition(":")
    return _tiene_permiso(user, modulo, accion or "ver")
