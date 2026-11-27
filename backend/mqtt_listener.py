import json
import math
import sqlite3
import time
import uuid
import paho.mqtt.client as mqtt

from database import (
    inicializar_db,
    guardar_lectura,
    guardar_evento,
    guardar_comando
)

BROKER = "broker.emqx.io"
PORT = 1883

DEVICE_ID = "invernadero-01"

TOPIC_SENSORES = "invernadero/01/sensores"
TOPIC_EVENTOS = "invernadero/01/eventos"
TOPIC_ESTADO = "invernadero/01/estado"


def validar_numero(valor, minimo, maximo):
    return (
        type(valor) in (int, float)
        and math.isfinite(valor)
        and minimo <= valor <= maximo
    )


def on_connect(cliente, userdata, flags,
               reason_code, properties):

    if reason_code == 0:
        print("Conectado a EMQX")

        cliente.subscribe([
            (TOPIC_SENSORES, 0),
            (TOPIC_EVENTOS, 0),
            (TOPIC_ESTADO, 0)
        ])

        print("Esperando mensajes del invernadero...")

    else:
        print("Error de conexion:", reason_code)


def on_message(cliente, userdata, mensaje):
    try:
        datos = json.loads(
            mensaje.payload.decode("utf-8")
        )

        if not isinstance(datos, dict):
            raise ValueError("Mensaje invalido")

        if datos.get("device_id") != DEVICE_ID:
            return

        if mensaje.topic == TOPIC_SENSORES:

            if not validar_numero(
                datos["temperatura"], -40, 80
            ):
                raise ValueError("Temperatura invalida")

            if not validar_numero(
                datos["humedad"], 0, 100
            ):
                raise ValueError("Humedad invalida")

            if not validar_numero(
                datos["luminosidad"], 0, 100
            ):
                raise ValueError("Luminosidad invalida")

            guardar_lectura(datos)
            print("LECTURA GUARDADA:", datos)

        elif mensaje.topic == TOPIC_EVENTOS:

            if not all(
                isinstance(datos[campo], str)
                and datos[campo].strip()
                for campo in ("tipo", "descripcion")
            ):
                raise ValueError("Evento invalido")

            guardar_evento(datos)
            print("EVENTO GUARDADO:", datos)

        elif mensaje.topic == TOPIC_ESTADO:

            if datos["actuador"] not in (
                "ventilacion",
                "iluminacion",
                "riego"
            ):
                raise ValueError("Actuador invalido")

            if datos["estado"] not in ("ON", "OFF"):
                raise ValueError("Estado invalido")

            command_id = datos["command_id"]

            if command_id is not None and (
                not isinstance(command_id, str)
                or not command_id.strip()
            ):
                raise ValueError("Comando invalido")

            if not isinstance(datos["resultado"], str):
                raise ValueError("Resultado invalido")

            guardar_comando(datos)
            print("ESTADO GUARDADO:", datos)

    except (ValueError, KeyError, TypeError,
            sqlite3.Error) as error:

        print("Mensaje rechazado:", error)


def main():
    inicializar_db()

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="backend-" + uuid.uuid4().hex[:12]
    )

    cliente.on_connect = on_connect
    cliente.on_message = on_message

    cliente.reconnect_delay_set(
        min_delay=1,
        max_delay=30
    )

    while True:
        try:
            cliente.connect(BROKER, PORT, 60)
            break
        except OSError as error:
            print("MQTT: reintentando conexion en 2s...", error)
            time.sleep(2)

    try:
        cliente.loop_forever()

    except KeyboardInterrupt:
        cliente.disconnect()
        print("Backend detenido")


if __name__ == "__main__":
    main()