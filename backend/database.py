import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "backend" / "invernadero.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def timestamp_utc():
    return datetime.now(timezone.utc).isoformat()


def inicializar_db():
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.executescript(
            SCHEMA_PATH.read_text(encoding="utf-8")
        )

    print("Base de datos inicializada:", DB_PATH)


def guardar_lectura(datos):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            INSERT INTO lecturas (
                device_id, temperatura, humedad,
                luminosidad, timestamp
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datos["device_id"],
                datos["temperatura"],
                datos["humedad"],
                datos["luminosidad"],
                timestamp_utc()
            )
        )


def guardar_evento(datos):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            INSERT INTO eventos (
                device_id, tipo, descripcion, timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                datos["device_id"],
                datos["tipo"],
                datos["descripcion"],
                timestamp_utc()
            )
        )


def guardar_comando(datos):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            INSERT INTO comandos (
                device_id, command_id, actuador,
                estado, resultado, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datos["device_id"],
                datos["command_id"],
                datos["actuador"],
                datos["estado"],
                datos["resultado"],
                timestamp_utc()
            )
        )


def consultar_lecturas(limite=20):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        registros = conexion.execute(
            """
            SELECT * FROM lecturas
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,)
        ).fetchall()

        return [dict(registro) for registro in registros]


if __name__ == "__main__":
    inicializar_db()