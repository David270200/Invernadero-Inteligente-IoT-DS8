# Interfaz compartida de sensores

## Invernadero Inteligente IoT

Este documento define la interfaz entre el módulo de sensores (integrante 1) y el módulo de comunicación MQTT (integrante 2).

### Función principal

`leer_sensores()`

**Ubicación:** `wokwi/sensores.py`

**Responsable:** Integrante 1.

### Datos devueltos

La función devolverá un diccionario de Python:

```python
{
    "device_id": "invernadero-01",
    "temperatura": 32.5,
    "humedad": 65.0,
    "luminosidad": 40.0
}
```

### Tipos de datos

| Campo | Tipo | Descripción |
|---|---|---|
| device_id | str | Identificador del dispositivo |
| temperatura | float | Temperatura en °C |
| humedad | float | Humedad relativa, 0–100% |
| luminosidad | float | Luminosidad normalizada, 0–100% |

### Reglas

1. Los valores numéricos deben estar validados.
2. La función no debe publicar mensajes MQTT.
3. La función no debe controlar actuadores.
4. El módulo MQTT será responsable de convertir el diccionario a JSON y publicarlo.
5. Si ocurre un error de lectura, la función generará una excepción para que el módulo principal pueda manejarla.
6. No se modificarán los nombres de los campos sin acuerdo del equipo.

### Ejemplo de integración

```python
from sensores import leer_sensores

datos = leer_sensores()

# El integrante 2 implementará la publicación MQTT.
# mqtt.publicar(datos)
```

### Responsabilidades

**Integrante 1:** implementar y probar `leer_sensores()`.

**Integrante 2:** utilizar la función para publicar las lecturas mediante MQTT.

Esta separación permite desarrollar ambos módulos de manera independiente.
