from machine import Pin

ventilacion = Pin(16, Pin.OUT)
iluminacion = Pin(17, Pin.OUT)
riego = Pin(18, Pin.OUT)

actuadores = {
    "ventilacion": ventilacion,
    "iluminacion": iluminacion,
    "riego": riego
}

# Inicializar todos los actuadores apagados
for actuador in actuadores.values():
    actuador.off()


def controlar_actuador(nombre, estado):
    if nombre not in actuadores:
        raise ValueError("Actuador desconocido")

    if estado not in (0, 1):
        raise ValueError("Estado no valido")

    actuadores[nombre].value(estado)

    return actuadores[nombre].value()


def obtener_estados():
    return {
        nombre: pin.value()
        for nombre, pin in actuadores.items()
    }