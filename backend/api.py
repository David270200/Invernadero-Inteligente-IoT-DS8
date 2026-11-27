import os
import json
import uuid
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "backend" / "invernadero.db"

load_dotenv(ROOT / ".env")

BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))

DEVICE_ID = "invernadero-01"
TOPIC_COMANDOS = "invernadero/01/comandos"

cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="dashboard-" + uuid.uuid4().hex[:8]
)


@asynccontextmanager
async def lifespan(app):
    cliente.connect_async(BROKER, PORT, 60)
    cliente.loop_start()
    yield
    cliente.disconnect()
    cliente.loop_stop()


app = FastAPI(
    title="GreenHouse IoT API",
    lifespan=lifespan
)


def consultar(sql, parametros=()):
    conexion = sqlite3.connect(DB, timeout=5)
    conexion.row_factory = sqlite3.Row

    try:
        filas = conexion.execute(sql, parametros).fetchall()
        return [dict(fila) for fila in filas]
    finally:
        conexion.close()


@app.get("/api/lecturas")
def lecturas():
    datos = consultar(
        """SELECT * FROM lecturas
           WHERE device_id = ?
           ORDER BY id DESC LIMIT 60""",
        (DEVICE_ID,)
    )
    return datos[::-1]


@app.get("/api/actual")
def actual():
    datos = consultar(
        """SELECT * FROM lecturas
           WHERE device_id = ?
           ORDER BY id DESC LIMIT 1""",
        (DEVICE_ID,)
    )
    return datos[0] if datos else {}


@app.get("/api/eventos")
def eventos():
    return consultar(
        """SELECT * FROM eventos
           WHERE device_id = ?
           ORDER BY id DESC LIMIT 20""",
        (DEVICE_ID,)
    )


@app.get("/api/estados")
def estados():
    resultado = {
        "ventilacion": "DESCONOCIDO",
        "iluminacion": "DESCONOCIDO",
        "riego": "DESCONOCIDO"
    }

    for actuador in resultado:
        datos = consultar(
            """SELECT estado FROM comandos
               WHERE device_id = ? AND actuador = ?
               AND resultado = 'ejecutado'
               ORDER BY id DESC LIMIT 1""",
            (DEVICE_ID, actuador)
        )

        if datos:
            resultado[actuador] = datos[0]["estado"]

    return resultado


@app.get("/api/conexion")
def conexion():
    return {"mqtt": cliente.is_connected()}


class Comando(BaseModel):
    actuador: str
    accion: str


@app.post("/api/comandos")
def enviar_comando(datos: Comando):

    permitidos = {
        "ventilacion": ["ON", "OFF"],
        "iluminacion": ["ON", "OFF"],
        "riego": ["PULSE"]
    }

    if datos.actuador not in permitidos:
        raise HTTPException(400, "Actuador invalido")

    if datos.accion not in permitidos[datos.actuador]:
        raise HTTPException(400, "Accion invalida")

    if not cliente.is_connected():
        raise HTTPException(503, "MQTT desconectado")

    comando = {
        "command_id": str(uuid.uuid4()),
        "actuador": datos.actuador,
        "accion": datos.accion,
        "origen": "dashboard"
    }

    resultado = cliente.publish(
        TOPIC_COMANDOS,
        json.dumps(comando),
        qos=0,
        retain=False
    )

    if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
        raise HTTPException(503, "No se pudo enviar")

    return {
        "mensaje": "Comando enviado",
        "command_id": comando["command_id"]
    }


app.mount(
    "/",
    StaticFiles(directory=ROOT / "frontend", html=True),
    name="frontend"
)