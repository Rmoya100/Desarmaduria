-- Script de configuracion inicial de MySQL para este proyecto.
-- Ejecutar UNA SOLA VEZ, con un usuario administrador de MySQL (ej. root):
--   mysql -u root -p < setup_mysql_usuario.sql
--
-- Antes de ejecutar: reemplaza CAMBIA_ESTA_PASSWORD por el valor de
-- DB_PASSWORD definido en tu archivo .env (no se versiona). No subas este
-- archivo a git con la password real reemplazada.
--
-- Crea la base de datos (si no existe) y un usuario dedicado para la app
-- Django, con privilegios solo sobre esa base: principio de minimo
-- privilegio, la app nunca deberia conectarse a MySQL como root.

CREATE DATABASE IF NOT EXISTS desarmaduria
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'desarmaduria_app'@'localhost'
    IDENTIFIED BY 'CAMBIA_ESTA_PASSWORD';
CREATE USER IF NOT EXISTS 'desarmaduria_app'@'127.0.0.1'
    IDENTIFIED BY 'CAMBIA_ESTA_PASSWORD';

GRANT ALL PRIVILEGES ON desarmaduria.* TO 'desarmaduria_app'@'localhost';
GRANT ALL PRIVILEGES ON desarmaduria.* TO 'desarmaduria_app'@'127.0.0.1';

FLUSH PRIVILEGES;
