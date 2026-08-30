"""Modelos ORM (SQLAlchemy 2.0) para la base de datos `desarmaduria`.

Generado a partir de schema_desarmaduria.sql. Estilo declarativo con
`Mapped` / `mapped_column` y tipos del dialecto MySQL.

Uso rapido
----------
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from modelo import Base, Usuario

    engine = create_engine(
        "mysql+pymysql://usuario:password@localhost:3306/desarmaduria"
    )
    Base.metadata.create_all(engine)  # crea las tablas si no existen

    with Session(engine) as s:
        s.add(Usuario(nombreUsuario="Ana", email="ana@x.cl",
                      username="ana", passwordHash="...", idRol=1))
        s.commit()

Dependencias: SQLAlchemy>=2.0, PyMySQL (o mysqlclient).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER, MEDIUMINT, SMALLINT, TINYINT, YEAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Tipos MySQL UNSIGNED reutilizables
TinyPK = TINYINT(unsigned=True)
SmallPK = SMALLINT(unsigned=True)
MediumPK = MEDIUMINT(unsigned=True)
IntPK = INTEGER(unsigned=True)


class Base(DeclarativeBase):
    """Base declarativa comun a todos los modelos."""


# ---------------------------------------------------------------------------
# Seguridad / usuarios
# ---------------------------------------------------------------------------
class Rol(Base):
    __tablename__ = "rol"

    idRol: Mapped[int] = mapped_column(TinyPK, primary_key=True, autoincrement=True)
    nombreRol: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    permisos: Mapped[list["RolPermiso"]] = relationship(back_populates="rol")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class Permiso(Base):
    __tablename__ = "permiso"
    __table_args__ = (UniqueConstraint("modulo", "nombrePermiso"),)

    idPermiso: Mapped[int] = mapped_column(SmallPK, primary_key=True, autoincrement=True)
    nombrePermiso: Mapped[str] = mapped_column(String(50), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)

    roles: Mapped[list["RolPermiso"]] = relationship(back_populates="permiso")


class RolPermiso(Base):
    __tablename__ = "rolPermiso"

    idRol: Mapped[int] = mapped_column(
        TinyPK, ForeignKey("rol.idRol"), primary_key=True
    )
    idPermiso: Mapped[int] = mapped_column(
        SmallPK, ForeignKey("permiso.idPermiso"), primary_key=True
    )

    rol: Mapped["Rol"] = relationship(back_populates="permisos")
    permiso: Mapped["Permiso"] = relationship(back_populates="roles")


class Usuario(Base):
    __tablename__ = "usuario"

    idUsuario: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    nombreUsuario: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    passwordHash: Mapped[str] = mapped_column(String(255), nullable=False)
    idRol: Mapped[int] = mapped_column(TinyPK, ForeignKey("rol.idRol"), nullable=False)
    activo: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default=text("1")
    )
    fechaCreacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    ultimoAcceso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rol: Mapped["Rol"] = relationship(back_populates="usuarios")
    ventas: Mapped[list["Venta"]] = relationship(back_populates="usuario")
    entradas: Mapped[list["Entrada"]] = relationship(back_populates="usuario")
    gastos: Mapped[list["Gasto"]] = relationship(back_populates="usuario")


# ---------------------------------------------------------------------------
# Vehiculos
# ---------------------------------------------------------------------------
class Marca(Base):
    __tablename__ = "marca"

    idMarca: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    nombreMarca: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    modelos: Mapped[list["Modelo"]] = relationship(back_populates="marca")


class Modelo(Base):
    __tablename__ = "modelo"
    __table_args__ = (UniqueConstraint("idMarca", "nombreModelo"),)

    idModelo: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    idMarca: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("marca.idMarca"), nullable=False
    )
    nombreModelo: Mapped[str] = mapped_column(String(50), nullable=False)

    marca: Mapped["Marca"] = relationship(back_populates="modelos")
    vehiculos: Mapped[list["Vehiculo"]] = relationship(back_populates="modelo")


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    idVehiculo: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    idModelo: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("modelo.idModelo"), nullable=False
    )
    anio: Mapped[int] = mapped_column(YEAR, nullable=False)
    patente: Mapped[str | None] = mapped_column(String(10), nullable=True, unique=True)

    modelo: Mapped["Modelo"] = relationship(back_populates="vehiculos")
    productos: Mapped[list["Producto"]] = relationship(back_populates="vehiculo")
    entradas: Mapped[list["Entrada"]] = relationship(back_populates="vehiculo")


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------
class Categoria(Base):
    __tablename__ = "categoria"

    idCategoria: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    nombreCategoria: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )

    productos: Mapped[list["Producto"]] = relationship(back_populates="categoria")


class Producto(Base):
    __tablename__ = "producto"

    idProducto: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    idCategoria: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("categoria.idCategoria"), nullable=False
    )
    idVehiculo: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("vehiculo.idVehiculo"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    costo: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)

    categoria: Mapped["Categoria"] = relationship(back_populates="productos")
    vehiculo: Mapped["Vehiculo"] = relationship(back_populates="productos")
    detallesVenta: Mapped[list["DetalleVenta"]] = relationship(
        back_populates="producto"
    )
    detallesEntrada: Mapped[list["DetalleEntrada"]] = relationship(
        back_populates="producto"
    )


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------
class FormaPago(Base):
    __tablename__ = "formaPago"

    idFormaPago: Mapped[int] = mapped_column(
        TinyPK, primary_key=True, autoincrement=True
    )
    formaPago: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    ventas: Mapped[list["Venta"]] = relationship(back_populates="formaPago")


class TipoDocumento(Base):
    __tablename__ = "tipoDocumento"

    idTipoDocumento: Mapped[int] = mapped_column(
        TinyPK, primary_key=True, autoincrement=True
    )
    tipoDocumento: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    ventas: Mapped[list["Venta"]] = relationship(back_populates="tipoDocumento")


class Venta(Base):
    __tablename__ = "venta"

    idVenta: Mapped[int] = mapped_column(IntPK, primary_key=True, autoincrement=True)
    fechaVenta: Mapped[date] = mapped_column(Date, nullable=False)
    idTipoDocumento: Mapped[int] = mapped_column(
        TinyPK, ForeignKey("tipoDocumento.idTipoDocumento"), nullable=False
    )
    idFormaPago: Mapped[int] = mapped_column(
        TinyPK, ForeignKey("formaPago.idFormaPago"), nullable=False
    )
    idUsuario: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("usuario.idUsuario"), nullable=False
    )
    fechaRegistro: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    tipoDocumento: Mapped["TipoDocumento"] = relationship(back_populates="ventas")
    formaPago: Mapped["FormaPago"] = relationship(back_populates="ventas")
    usuario: Mapped["Usuario"] = relationship(back_populates="ventas")
    detalles: Mapped[list["DetalleVenta"]] = relationship(back_populates="venta")


class DetalleVenta(Base):
    __tablename__ = "detalleVenta"

    idDetalleVenta: Mapped[int] = mapped_column(
        IntPK, primary_key=True, autoincrement=True
    )
    idVenta: Mapped[int] = mapped_column(
        IntPK, ForeignKey("venta.idVenta"), nullable=False
    )
    idProducto: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("producto.idProducto"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(MediumPK, nullable=False)
    precio: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    venta: Mapped["Venta"] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship(back_populates="detallesVenta")


# ---------------------------------------------------------------------------
# Entradas de stock
# ---------------------------------------------------------------------------
class Entrada(Base):
    __tablename__ = "entrada"

    idEntrada: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    idVehiculo: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("vehiculo.idVehiculo"), nullable=False
    )
    idUsuario: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("usuario.idUsuario"), nullable=False
    )
    fechaRegistro: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    vehiculo: Mapped["Vehiculo"] = relationship(back_populates="entradas")
    usuario: Mapped["Usuario"] = relationship(back_populates="entradas")
    detalles: Mapped[list["DetalleEntrada"]] = relationship(back_populates="entrada")


class DetalleEntrada(Base):
    __tablename__ = "detalleEntrada"

    idDetalleEntrada: Mapped[int] = mapped_column(
        IntPK, primary_key=True, autoincrement=True
    )
    idEntrada: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("entrada.idEntrada"), nullable=False
    )
    idProducto: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("producto.idProducto"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(MediumPK, nullable=False)

    entrada: Mapped["Entrada"] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship(back_populates="detallesEntrada")


# ---------------------------------------------------------------------------
# Gastos
# ---------------------------------------------------------------------------
class ConceptoGasto(Base):
    __tablename__ = "conceptoGasto"

    idConcepto: Mapped[int] = mapped_column(
        MediumPK, primary_key=True, autoincrement=True
    )
    nombreGasto: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    gastos: Mapped[list["Gasto"]] = relationship(back_populates="concepto")


class Gasto(Base):
    __tablename__ = "gasto"

    idGasto: Mapped[int] = mapped_column(IntPK, primary_key=True, autoincrement=True)
    idConcepto: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("conceptoGasto.idConcepto"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idUsuario: Mapped[int] = mapped_column(
        MediumPK, ForeignKey("usuario.idUsuario"), nullable=False
    )
    fechaRegistro: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    concepto: Mapped["ConceptoGasto"] = relationship(back_populates="gastos")
    usuario: Mapped["Usuario"] = relationship(back_populates="gastos")


__all__ = [
    "Base",
    "Rol",
    "Permiso",
    "RolPermiso",
    "Usuario",
    "Marca",
    "Modelo",
    "Vehiculo",
    "Categoria",
    "Producto",
    "FormaPago",
    "TipoDocumento",
    "Venta",
    "DetalleVenta",
    "Entrada",
    "DetalleEntrada",
    "ConceptoGasto",
    "Gasto",
]
