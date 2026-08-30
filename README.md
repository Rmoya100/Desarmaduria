# Desarmaduria

Proyecto Django (Python) para la gestion de una desarmaduria: usuarios y roles,
catalogo de vehiculos (marca / modelo / vehiculo), productos, ventas, entradas de
stock y gastos.

- **Framework:** Django 5.0
- **Base de datos:** MySQL 8 (driver PyMySQL)
- **Proyecto:** `desarmaduria`  ·  **App principal:** `inventario`

## Requisitos

- Python 3.12+
- MySQL 8 en ejecucion

## Puesta en marcha

```bash
# 1. Entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 2. Dependencias
pip install -r requirements.txt

# 3. Configuracion
copy .env.example .env        # Windows  (cp en Linux/macOS)
#   edita .env con tus credenciales de MySQL

# 4. Crear la base (si no existe)
#   En MySQL:  CREATE DATABASE desarmaduria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 5. Migraciones
python manage.py makemigrations
python manage.py migrate

# 6. Usuario admin y servidor
python manage.py createsuperuser
python manage.py runserver
```

Panel de administracion en `http://127.0.0.1:8000/admin/`.

## Modelos (`inventario/models.py`)

Portados desde `schema_desarmaduria.sql`. Se conservan los nombres de tabla y
columna originales via `Meta.db_table` y `db_column`.

| Tabla | Modelo |
|-------|--------|
| `rol` | `Rol` |
| `permiso` | `Permiso` |
| `rolPermiso` | `RolPermiso` |
| `usuario` | `Usuario` |
| `marca` | `Marca` |
| `modelo` | `Modelo` |
| `vehiculo` | `Vehiculo` |
| `categoria` | `Categoria` |
| `producto` | `Producto` |
| `formaPago` | `FormaPago` |
| `tipoDocumento` | `TipoDocumento` |
| `venta` | `Venta` |
| `detalleVenta` | `DetalleVenta` |
| `entrada` | `Entrada` |
| `detalleEntrada` | `DetalleEntrada` |
| `conceptoGasto` | `ConceptoGasto` |
| `gasto` | `Gasto` |

Diferencias respecto al SQL original: PK `UNSIGNED` -> `AutoField` (INT);
`TINYINT(1)` -> `BooleanField`; `YEAR` -> `PositiveSmallIntegerField`;
`rolPermiso` usa PK surrogada + UNIQUE en lugar de PK compuesta.
