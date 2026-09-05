"""Sobrescribe el formato numerico de Django para es-cl.

El locale generico "es" de Django usa un espacio irrompible como separador de
miles (estandar CLDR), pero en Chile se usa punto: $193.000, no $193 000.
"""

DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
