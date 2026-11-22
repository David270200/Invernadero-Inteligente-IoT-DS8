# 🌱 Invernadero Inteligente IoT

## 📌 Descripción del proyecto

Este proyecto corresponde al **Parcial #2 de Desarrollo de Software VIII** de la Universidad Tecnológica de Panamá (UTP).

Consiste en desarrollar un sistema IoT para simular el monitoreo y control de un invernadero inteligente, utilizando sensores, actuadores, comunicación MQTT, almacenamiento de datos y una plataforma en la nube.

El sistema permitirá monitorear las condiciones ambientales del invernadero y controlar dispositivos de manera automática o remota.

## 🎯 Objetivo general

Desarrollar un sistema IoT de monitoreo y control inteligente que permita recopilar, procesar, almacenar y visualizar información ambiental de un invernadero mediante tecnologías de comunicación y servicios en la nube.

## ⚙️ Funcionalidades previstas

- Monitoreo de temperatura y humedad ambiental.
- Medición de luminosidad.
- Control automático de ventilación e iluminación simuladas.
- Activación remota de un sistema de riego simulado.
- Comunicación bidireccional mediante MQTT.
- Almacenamiento de lecturas y eventos en una base de datos.
- Consulta de registros históricos.
- Visualización de información en un dashboard Cloud.
- Control remoto de actuadores desde la nube.

## 🛠️ Tecnologías

| Tecnología | Función |
|---|---|
| Python / MicroPython | Programación del sistema |
| Wokwi | Simulación del circuito |
| Raspberry Pi Pico W | Microcontrolador |
| DHT22 | Temperatura y humedad |
| LDR | Sensor de luminosidad |
| LEDs | Simulación de actuadores |
| MQTT / HiveMQ Cloud | Comunicación |
| SQLite | Almacenamiento |
| Adafruit IO | Dashboard y control remoto |
| GitHub | Control de versiones |

## 🏗️ Arquitectura propuesta

```text
         INVERNADERO INTELIGENTE
                    |
          Raspberry Pi Pico W
             (Wokwi)
                    |
          Sensores y actuadores
                    |
                   MQTT
                    |
              HiveMQ Cloud
                    |
             Servicio Python
                    |
           +--------+--------+
           |                 |
         SQLite          Adafruit IO
           |                 |
       Históricos         Dashboard
                         y controles
```

Los comandos remotos seguirán el camino inverso desde Adafruit IO hacia el dispositivo mediante el servicio Python y MQTT.

## 👨‍💻 Distribución del equipo

**Integrante 1 — Sensores y monitoreo**

Responsable de configurar y programar los sensores, obtener lecturas ambientales y detectar condiciones que requieran acciones automáticas.

**Integrante 2 — Actuadores y MQTT**

Responsable de programar los actuadores, implementar la comunicación MQTT y recibir comandos de control.

**Integrante 3 — Base de datos e históricos**

Responsable de desarrollar el almacenamiento de lecturas, eventos y comandos, además de implementar consultas históricas.

**Integrante 4 — Dashboard Cloud e integración**

Responsable de configurar Adafruit IO, implementar la visualización de datos y desarrollar la comunicación entre la nube y el broker MQTT.

Todos los integrantes participarán en las pruebas, documentación, integración y sustentación del proyecto.

## 📂 Estructura prevista

```text
Invernadero-Inteligente-IoT/
├── wokwi/
│   ├── diagram.json
│   ├── main.py
│   ├── sensores.py
│   ├── actuadores.py
│   └── mqtt_client.py
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── mqtt_listener.py
│   └── cloud_bridge.py
├── sql/
│   ├── schema.sql
│   └── consultas.sql
├── docs/
├── tests/
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

## 🚧 Estado del proyecto

**En desarrollo — Etapa 1: planificación técnica.**

Se han definido los componentes, las tecnologías, la arquitectura inicial y la distribución de responsabilidades.

Las conexiones MQTT, la simulación completa y la integración con la plataforma Cloud están pendientes de implementación y validación.

## 📚 Información académica

**Universidad:** Universidad Tecnológica de Panamá (UTP)

**Asignatura:** Desarrollo de Software VIII

**Evaluación:** Parcial #2

**Tema:** Invernadero Inteligente — Control de condiciones de cultivo

**Equipo:** 4 estudiantes

## 📄 Uso académico

Proyecto desarrollado con fines educativos como parte de la evaluación de la asignatura Desarrollo de Software VIII.
