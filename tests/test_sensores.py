import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


RUTA_SENSORES = (
    Path(__file__).resolve().parents[1]
    / "wokwi"
    / "sensores.py"
)


class TestSensores(unittest.TestCase):

    def setUp(self):
        # Simulamos las bibliotecas de MicroPython
        self.machine = ModuleType("machine")
        self.dht = ModuleType("dht")

        self.machine.Pin = MagicMock()
        self.machine.ADC = MagicMock()
        self.dht.DHT22 = MagicMock()

        # Valores iniciales de prueba
        self.sensor_dht = self.dht.DHT22.return_value
        self.sensor_ldr = self.machine.ADC.return_value

        self.sensor_dht.temperature.return_value = 24.0
        self.sensor_dht.humidity.return_value = 40.0
        self.sensor_ldr.read_u16.return_value = 32768

        # Cargamos sensores.py usando los módulos simulados
        with patch.dict(sys.modules, {
            "machine": self.machine,
            "dht": self.dht
        }):
            spec = importlib.util.spec_from_file_location(
                "sensores_bajo_prueba",
                RUTA_SENSORES
            )
            self.modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.modulo)

    def test_estructura_datos(self):
        datos = self.modulo.leer_sensores()

        self.assertEqual(
            set(datos.keys()),
            {
                "device_id",
                "temperatura",
                "humedad",
                "luminosidad"
            }
        )

    def test_lecturas_validas(self):
        datos = self.modulo.leer_sensores()

        self.assertEqual(datos["device_id"], "invernadero-01")
        self.assertEqual(datos["temperatura"], 24.0)
        self.assertEqual(datos["humedad"], 40.0)
        self.assertAlmostEqual(datos["luminosidad"], 50.0, places=2)

        self.sensor_dht.measure.assert_called_once()

    def test_temperatura_fuera_de_rango(self):
        self.sensor_dht.temperature.return_value = 100

        with self.assertRaisesRegex(
            ValueError, "Temperatura fuera de rango"
        ):
            self.modulo.leer_sensores()

    def test_humedad_fuera_de_rango(self):
        self.sensor_dht.humidity.return_value = 120

        with self.assertRaisesRegex(
            ValueError, "Humedad fuera de rango"
        ):
            self.modulo.leer_sensores()

    def test_oscuridad(self):
        self.sensor_ldr.read_u16.return_value = 65535

        datos = self.modulo.leer_sensores()

        self.assertEqual(datos["luminosidad"], 0.0)

    def test_mucha_luz(self):
        self.sensor_ldr.read_u16.return_value = 0

        datos = self.modulo.leer_sensores()

        self.assertEqual(datos["luminosidad"], 100.0)


if __name__ == "__main__":
    unittest.main()