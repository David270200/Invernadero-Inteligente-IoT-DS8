# Contrato de comunicación MQTT

## Proyecto: Invernadero Inteligente IoT

Este documento establece los formatos y tópicos de comunicación que utilizarán los cuatro módulos del sistema.

**Identificador del dispositivo:** `invernadero-01`

**Broker propuesto:** HiveMQ Cloud

**Formato de mensajes:** JSON

## 1. Tópicos MQTT

| Tópico | Descripción |
|---|---|
| `invernadero/01/sensores` | Lecturas de los sensores |
| `invernadero/01/comandos` | Comandos enviados al dispositivo |
| `invernadero/01/estado` | Confirmación y estado de actuadores |
| `invernadero/01/eventos` | Alertas y eventos del sistema |

## 2. Mensaje de sensores

Publicado cada 5 segundos.

```json
{
  "device_id": "invernadero-01",
  "temperatura": 32.5,
  "humedad": 65.0,
  "luminosidad": 40.0
}
```

**Campos:**

- `device_id`: identificador único del dispositivo.
- `temperatura`: temperatura en grados Celsius.
- `humedad`: humedad relativa ambiental en porcentaje.
- `luminosidad`: nivel de luz normalizado de 0 a 100%.

Los tres valores de medición deben ser numéricos.

El servicio Python añadirá la fecha y hora UTC cuando reciba el mensaje.

## 3. Comandos remotos

```json
{
  "command_id": "cmd-001",
  "actuador": "riego",
  "accion": "PULSE",
  "origen": "cloud"
}
```

**Actuadores permitidos:**

- `ventilacion`
- `iluminacion`
- `riego`

**Acciones permitidas:**

- `ON`: encender ventilación o iluminación.
- `OFF`: apagar ventilación o iluminación.
- `PULSE`: activar el riego durante 5 segundos.

Cada comando debe tener un `command_id` único para evitar ejecuciones duplicadas.

## 4. Estado de los actuadores

Ejemplo de confirmación:

```json
{
  "device_id": "invernadero-01",
  "command_id": "cmd-001",
  "actuador": "riego",
  "estado": "ON",
  "resultado": "ejecutado"
}
```

El dispositivo también publicará los cambios automáticos de estado. Cuando no exista un comando asociado, `command_id` será `null`.

## 5. Eventos

Ejemplo de evento:

```json
{
  "device_id": "invernadero-01",
  "tipo": "temperatura_alta",
  "descripcion": "La temperatura superó los 30 grados Celsius"
}
```

Los eventos se publicarán cuando ocurra un cambio relevante, evitando enviar repetidamente la misma alerta.

## 6. Reglas automáticas

| Condición | Acción |
|---|---|
| Temperatura > 30 °C | Encender ventilación |
| Temperatura <= 28 °C | Apagar ventilación |
| Luminosidad < 30% | Encender iluminación |
| Luminosidad > 40% | Apagar iluminación |
| Comando de riego `PULSE` | Activar riego durante 5 segundos |

Entre los umbrales de encendido y apagado se conserva el estado anterior para evitar cambios constantes.

## 7. Responsabilidades

**Integrante 1:** generar lecturas de sensores y detectar condiciones ambientales.

**Integrante 2:** publicar las lecturas mediante MQTT, controlar actuadores y recibir comandos.

**Integrante 3:** almacenar lecturas, eventos y confirmaciones de comandos en SQLite.

**Integrante 4:** visualizar información y enviar comandos desde Adafruit IO mediante el puente de integración.

## 8. Reglas de integración

- No modificar los nombres de tópicos sin acuerdo del equipo.
- Mantener los nombres de los campos JSON.
- Utilizar los mismos identificadores de actuadores.
- No publicar credenciales en GitHub.
- Validar los mensajes antes de procesarlos.
- Documentar cualquier cambio en este contrato.
