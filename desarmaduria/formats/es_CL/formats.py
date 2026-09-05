# Django trae el separador de miles del locale "es" como espacio fino
# (recomendacion ISO), pero en Chile el uso real es el punto: $1.234.567,89.
# Se activa via FORMAT_MODULE_PATH en settings.py.
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
NUMBER_GROUPING = 3
