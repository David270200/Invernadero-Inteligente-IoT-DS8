import os
import json
import uuid
import time
import paho.mqtt.client as mqtt
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
PORT = int(os.getenv("MQTT_PORT", "1883"))

DEVICE_ID = "invernadero-01"

TOPIC_SENSORES = "invernadero/01/sensores"
TOPIC_ESTADO = "invernadero/01/estado"
TOPIC_COMANDOS = "invernadero/01/comandos"

ACTUADORES = ("ventilacion", "iluminacion", "riego")

ultima_publicacion = 0


def feed_topic(feed):
    return f"{AIO_USERNAME}/feeds/{feed}"


def publicar_adafruit(feed, valor):
    if cloud.is_connected():
        cloud.publish(feed_topic(feed), str(valor))


def on_emqx_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("EMQX conectado")

        client.subscribe([
            (TOPIC_SENSORES, 0),
            (TOPIC_ESTADO, 0)
        ])
    else:
        print("Error EMQX:", reason_code)


def on_emqx_message(client, userdata, message):
    global ultima_publicacion

    try:
        datos = json.loads(message.payload.decode())

        if datos.get("device_id") != DEVICE_ID:
            return

        if message.topic == TOPIC_SENSORES:

            if not cloud.is_connected():
                return

            ahora = time.monotonic()

            # Limitar publicaciones para el plan gratuito.
            if ahora - ultima_publicacion < 15:
                return

            for campo in ("temperatura", "humedad", "luminosidad"):
                publicar_adafruit(campo, datos[campo])

            ultima_publicacion = ahora
            print("Sensores enviados a Adafruit IO:", datos)

        elif message.topic == TOPIC_ESTADO:

            actuador = datos["actuador"]
            estado = datos["estado"]

            if actuador in ACTUADORES and estado in ("ON", "OFF"):
                publicar_adafruit(f"estado-{actuador}", estado)
                print("Estado actualizado:", actuador, estado)

    except Exception as error:
        print("Error procesando mensaje:", error)


def on_cloud_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Adafruit IO conectado")

        for actuador in ACTUADORES:
            client.subscribe(feed_topic(actuador))

    else:
        print("Error Adafruit IO:", reason_code)


def on_cloud_message(client, userdata, message):

    try:
        actuador = message.topic.split("/")[-1]
        accion = message.payload.decode().strip().upper()

        if actuador not in ACTUADORES:
            return

        if actuador == "riego":
            if accion != "PULSE":
                return
        elif accion not in ("ON", "OFF"):
            return

        if not emqx.is_connected():
            print("Comando no enviado: EMQX desconectado")
            return

        comando = {
            "command_id": str(uuid.uuid4()),
            "actuador": actuador,
            "accion": accion,
            "origen": "cloud"
        }

        emqx.publish(
            TOPIC_COMANDOS,
            json.dumps(comando),
            qos=0,
            retain=False
        )

        print("Comando enviado a Wokwi:", comando)

    except Exception as error:
        print("Error procesando comando:", error)


emqx = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="bridge-emqx-" + uuid.uuid4().hex[:8]
)

cloud = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="bridge-aio-" + uuid.uuid4().hex[:8]
)

emqx.on_connect = on_emqx_connect
emqx.on_message = on_emqx_message

cloud.on_connect = on_cloud_connect
cloud.on_message = on_cloud_message


def main():

    if not AIO_USERNAME or not AIO_KEY:
        raise RuntimeError("Faltan las credenciales en .env")

    cloud.username_pw_set(AIO_USERNAME, AIO_KEY)
    cloud.tls_set()

    print("INICIANDO PUENTE CLOUD")

    cloud.connect("io.adafruit.com", 8883, 60)
    cloud.loop_start()

    while True:
        try:
            emqx.connect(BROKER, PORT, 60)
            break
        except OSError as error:
            print("EMQX: reintentando conexion en 2s...", error)
            time.sleep(2)

    try:
        emqx.loop_forever()

    except KeyboardInterrupt:
        print("Puente detenido")

    finally:
        emqx.disconnect()
        cloud.disconnect()
        cloud.loop_stop()


if __name__ == "__main__":
    main()