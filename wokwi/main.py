import time
import ujson

from sensores import leer_sensores
from actuadores import controlar_actuador, obtener_estados
from umqttsimple import MQTTException

from mqtt_client import (
    conectar_wifi,
    conectar_mqtt,
    publicar,
    TOPIC_SENSORES,
    TOPIC_COMANDOS,
    TOPIC_ESTADO,
    TOPIC_EVENTOS
)

DEVICE_ID = "invernadero-01"

cliente = None

riego_fin = None
riego_command_id = None

comandos_procesados = []

alerta_temperatura = False
alerta_luminosidad = False

mensajes_pendientes = []
MAX_PENDIENTES = 100


# Cerrar conexion perdida
def desconectar():

    global cliente

    anterior = cliente
    cliente = None

    if anterior is not None:

        try:

            if anterior.sock:
                anterior.sock.close()

        except OSError:
            pass


# Guardar eventos y confirmaciones pendientes
def guardar_pendiente(topic, datos):

    if topic == TOPIC_SENSORES:
        return

    if len(mensajes_pendientes) >= MAX_PENDIENTES:
        mensajes_pendientes.pop(0)

    mensajes_pendientes.append((topic, datos))


# Publicar sin detener el sistema
def publicar_seguro(topic, datos):

    if cliente is None:

        guardar_pendiente(topic, datos)

        return False

    try:

        publicar(cliente, topic, datos)

        return True

    except (OSError, MQTTException) as error:

        print("MQTT desconectado:", error)

        desconectar()

        guardar_pendiente(topic, datos)

        return False


# Enviar mensajes pendientes al reconectar
def enviar_pendientes():

    if cliente is None or not mensajes_pendientes:
        return

    topic, datos = mensajes_pendientes[0]

    try:

        publicar(cliente, topic, datos)

        mensajes_pendientes.pop(0)

    except (OSError, MQTTException) as error:

        print("Error enviando pendientes:", error)

        desconectar()


# Publicar eventos
def evento(tipo, descripcion):

    publicar_seguro(TOPIC_EVENTOS, {
        "device_id": DEVICE_ID,
        "tipo": tipo,
        "descripcion": descripcion
    })

    print("EVENTO:", descripcion)


# Publicar estado de actuadores
def publicar_estado(
    nombre,
    command_id=None,
    resultado="ejecutado"
):

    estado = obtener_estados()[nombre]

    publicar_seguro(TOPIC_ESTADO, {
        "device_id": DEVICE_ID,
        "command_id": command_id,
        "actuador": nombre,
        "estado": "ON" if estado else "OFF",
        "resultado": resultado
    })


# Cambiar estado de actuadores
def cambiar_estado(nombre, estado, command_id=None):

    anterior = obtener_estados()[nombre]

    controlar_actuador(nombre, estado)

    if anterior != estado or command_id is not None:

        publicar_estado(nombre, command_id)

        print(
            nombre,
            "ON" if estado else "OFF"
        )


# Evitar comandos duplicados
def regiMQTTExceptionar_comando(command_id):

    if len(comandos_procesados) >= 100:
        comandos_procesados.pop(0)

    comandos_procesados.append(command_id)


# Procesar comandos MQTT
def recibir_comando(topic, mensaje):

    global riego_fin, riego_command_id

    if topic != TOPIC_COMANDOS:
        return

    try:

        datos = ujson.loads(mensaje.decode())

        command_id = datos["command_id"]
        actuador = datos["actuador"]
        accion = datos["accion"]
        origen = datos["origen"]

        if not isinstance(command_id, str) or not command_id:
            raise ValueError("Identificador invalido")

        if not isinstance(origen, str) or not origen:
            raise ValueError("Origen invalido")

        if command_id in comandos_procesados:

            print("Comando duplicado:", command_id)

            return

        if actuador not in (
            "ventilacion",
            "iluminacion",
            "riego"
        ):

            raise ValueError("Actuador desconocido")

        if actuador == "riego":

            if accion != "PULSE":
                raise ValueError("Accion de riego invalida")

            if riego_fin is not None:

                publicar_estado(
                    actuador,
                    command_id,
                    "ocupado"
                )

                return

            riego_fin = time.ticks_add(
                time.ticks_ms(), 10000
            )

            riego_command_id = command_id

            regiMQTTExceptionar_comando(command_id)

            cambiar_estado(
                "riego", 1, command_id
            )

        else:

            if accion not in ("ON", "OFF"):
                raise ValueError("Accion invalida")

            regiMQTTExceptionar_comando(command_id)

            cambiar_estado(
                actuador,
                1 if accion == "ON" else 0,
                command_id
            )

        evento(
            "comando_ejecutado",
            actuador + ": " + accion
        )

    except (ValueError, KeyError, TypeError) as error:

        print("Comando rechazado:", error)


# Reglas automaticas
def control_automatico(datos):

    global alerta_temperatura
    global alerta_luminosidad

    temperatura = datos["temperatura"]
    luminosidad = datos["luminosidad"]

    # Ventilacion automatica
    if temperatura > 30:

        cambiar_estado("ventilacion", 1)

        if not alerta_temperatura:

            alerta_temperatura = True

            evento(
                "temperatura_alta",
                "La temperatura supero los 30 grados Celsius"
            )

    elif temperatura <= 28:

        cambiar_estado("ventilacion", 0)

        if alerta_temperatura:

            alerta_temperatura = False

            evento(
                "temperatura_normal",
                "La temperatura regreso al rango normal"
            )

    # Iluminacion automatica
    if luminosidad < 30:

        cambiar_estado("iluminacion", 1)

        if not alerta_luminosidad:

            alerta_luminosidad = True

            evento(
                "luminosidad_baja",
                "Luminosidad inferior al 30%"
            )

    elif luminosidad > 40:

        cambiar_estado("iluminacion", 0)

        if alerta_luminosidad:

            alerta_luminosidad = False

            evento(
                "luminosidad_normal",
                "Luminosidad superior al 40%"
            )


# Finalizar riego sin usar sleep de 5 segundos
def verificar_riego():

    global riego_fin, riego_command_id

    if riego_fin is not None:

        if time.ticks_diff(
            time.ticks_ms(), riego_fin
        ) >= 0:

            controlar_actuador("riego", 0)

            command_id = riego_command_id

            riego_fin = None
            riego_command_id = None

            publicar_estado("riego", command_id)

            evento(
                "riego_finalizado",
                "Ciclo de riego de 5 segundos completado"
            )


# ======================================
# PROGRAMA PRINCIPAL
# ======================================


def main():
    global cliente

    print("================================")
    print("INVERNADERO INTELIGENTE IoT")
    print("================================")

    ultima_lectura = time.ticks_add(
        time.ticks_ms(), -5000
    )

    ultimo_intento = time.ticks_add(
        time.ticks_ms(), -10000
    )

    ultimo_ping = time.ticks_ms()

    while True:

        ahora = time.ticks_ms()

        # Verificar temporizador de riego
        verificar_riego()

        # Leer sensores cada 5 segundos
        if time.ticks_diff(
            ahora, ultima_lectura
        ) >= 5000:

            ultima_lectura = ahora

            try:

                datos = leer_sensores()

            except (ValueError, OSError) as error:

                print("Error de sensor:", error)

                evento(
                    "error_sensor",
                    str(error)
                )

            else:

                print("SENSORES:", datos)

                # Control local independiente de MQTT
                control_automatico(datos)

                publicar_seguro(
                    TOPIC_SENSORES,
                    datos
                )

        # Evitar operaciones de red durante el riego
        # para no retrasar innecesariamente su apagado
        if riego_fin is not None:

            time.sleep_ms(50)

            continue

        # Gestionar conexion Wi-Fi y MQTT
        if cliente is None:

            try:

                wifi_disponible = conectar_wifi()

                if wifi_disponible:

                    if time.ticks_diff(
                        ahora, ultimo_intento
                    ) >= 10000:

                        ultimo_intento = ahora

                        cliente = conectar_mqtt(
                            recibir_comando
                        )

                        ultimo_ping = time.ticks_ms()

            except (OSError, MQTTException) as error:

                print("Error de conexion:", error)

                desconectar()

        else:

            try:

                # Recibir comandos remotos
                cliente.check_msg()

                if cliente is not None and riego_fin is None:

                    # Mantener conexion activa
                    if time.ticks_diff(
                        time.ticks_ms(), ultimo_ping
                    ) >= 20000:

                        cliente.ping()

                        ultimo_ping = time.ticks_ms()

                    # Recuperar eventos y estados pendientes
                    enviar_pendientes()

            except (OSError, MQTTException) as error:

                print("Conexion MQTT perdida:", error)

                desconectar()

        time.sleep_ms(100)


if __name__ == "__main__":
    main()