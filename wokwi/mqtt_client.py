import network
import time
import ujson
import os
import ubinascii

from umqttsimple import MQTTClient, MQTTException

DEVICE_ID = b"invernadero-01"
CLIENT_ID = b"greenhouse-" + ubinascii.hexlify(os.urandom(8))

BROKER = "broker.emqx.io"
PORT = 1883

TOPIC_SENSORES = b"invernadero/01/sensores"
TOPIC_COMANDOS = b"invernadero/01/comandos"
TOPIC_ESTADO = b"invernadero/01/estado"
TOPIC_EVENTOS = b"invernadero/01/eventos"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

wifi_inicio = None


def conectar_wifi():
    global wifi_inicio

    if wifi.isconnected():

        if wifi_inicio is not None:
            print("Wi-Fi conectado:", wifi.ifconfig())

        wifi_inicio = None
        return True

    ahora = time.ticks_ms()

    if wifi_inicio is None:

        print("Conectando Wi-Fi...")
        wifi.connect("Wokwi-GUEST", "")
        wifi_inicio = ahora

    elif time.ticks_diff(ahora, wifi_inicio) >= 60000:

        print("Reintentando Wi-Fi...")
        print("Estado Wi-Fi:", wifi.status())

        wifi.disconnect()
        wifi.connect("Wokwi-GUEST", "")

        wifi_inicio = ahora

    return False


def conectar_mqtt(callback):

    cliente = MQTTClient(
        CLIENT_ID,
        BROKER,
        port=PORT,
        keepalive=60
    )

    cliente.set_callback(callback)

    print("Conectando al broker MQTT...")
    print("Cliente MQTT:", CLIENT_ID)

    try:

        cliente.connect(timeout=30)
        cliente.subscribe(TOPIC_COMANDOS)

    except Exception:

        if cliente.sock:
            cliente.sock.close()

        raise

    print("MQTT conectado a EMQX")

    return cliente


def publicar(cliente, topic, datos):

    mensaje = ujson.dumps(datos)
    cliente.publish(topic, mensaje.encode())