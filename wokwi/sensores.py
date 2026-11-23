from machine import Pin, ADC
import dht

DEVICE_ID = "invernadero-01"

# Configuración de los sensores
sensor_dht = dht.DHT22(Pin(15))
sensor_ldr = ADC(Pin(26))


def leer_sensores():
    """
    Lee temperatura, humedad y luminosidad.
    Devuelve un diccionario compatible con MQTT.
    """

    # Lectura del DHT22
    sensor_dht.measure()
    temperatura = sensor_dht.temperature()
    humedad = sensor_dht.humidity()

    # Lectura del LDR
    valor_ldr = sensor_ldr.read_u16()
    luminosidad = (valor_ldr / 65535) * 100

    # Validación básica
    if not (-40 <= temperatura <= 80):
        raise ValueError("Temperatura fuera de rango")

    if not (0 <= humedad <= 100):
        raise ValueError("Humedad fuera de rango")

    return {
        "device_id": DEVICE_ID,
        "temperatura": round(temperatura, 2),
        "humedad": round(humedad, 2),
        "luminosidad": round(luminosidad, 2)
    }