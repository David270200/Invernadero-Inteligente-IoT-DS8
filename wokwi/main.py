
import time
from sensores import leer_sensores

print("Iniciando Invernadero Inteligente IoT...")

while True:
    try:
        # Obtener las lecturas del módulo
        datos = leer_sensores()

        print("----------------------------")
        print("Dispositivo:", datos["device_id"])
        print("Temperatura:", datos["temperatura"], "°C")
        print("Humedad:", datos["humedad"], "%")
        print("Luminosidad:", datos["luminosidad"], "%")

    except (OSError, ValueError) as error:
        print("Error de monitoreo:", error)

    time.sleep(5)