"""Usa PyMySQL como driver de MySQL (mas facil de instalar en Windows que
mysqlclient). Debe ejecutarse antes de que Django cargue el backend de BD.
"""

import pymysql

pymysql.install_as_MySQLdb()
