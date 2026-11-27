"""Tests del módulo principal del dispositivo (wokwi/main.py).

Simulan sensores, actuadores, mqtt_client y network con mocks
para probar la lógica de comandos, pérdida de conexión y reglas
automáticas sin conectarse a un broker real.
"""

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import re
from pathlib import Path

RUTA_WOKWI = Path(__file__).resolve().parents[1] / "wokwi"


def cargar_modulo(nombre, stubs):
    spec = importlib.util.spec_from_file_location(
        nombre, RUTA_WOKWI / f"{nombre}.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestMain(unittest.TestCase):
    def setUp(self):
        # Claves reales del programa del dispositivo (obtenidas por regex
        # del main para no tener que teclearlas)
        src_main = Path(
            RUTA_WOKWI / "main.py"
        ).read_text(encoding="utf-8")
        _keys = sorted(
            set(re.findall(r'datos\["([A-Za-z]+)"\]', src_main))
        )
        self.KEY_ACTVADOR = None
        for _k in _keys:
            if _k.startswith("a") and len(_k) >= 5 and "ct" in _k:
                self.KEY_ACTVADOR = _k
                break

        self._stub_keys = []
        self._stub_prev = {}

        machine = types.ModuleType("machine")
        machine.Pin = MagicMock()
        machine.ADC = MagicMock()

        dht = types.ModuleType("dht")
        dht.DHT22 = MagicMock()

        network = types.ModuleType("network")
        network.STA_IF = 1
        network.AP_IF = 0
        network.WLAN = MagicMock()

        ujson = types.ModuleType("ujson")
        ujson.dumps = json.dumps
        ujson.loads = json.loads

        # MicroPython 'time' incluye ticks_add/ticks_diff (añadimos stubs)
        import time as real_time

        time_mod = types.ModuleType("time")
        time_mod.time = real_time.time
        time_mod.sleep = real_time.sleep
        time_mod.sleep_ms = lambda ms: real_time.sleep(ms / 1000)

        def _ticks_ms():
            return int(real_time.time() * 1000)

        time_mod.ticks_ms = _ticks_ms
        time_mod.ticks_add = lambda ticks, delta: ticks + delta
        time_mod.ticks_diff = lambda a, b: a - b

        ubinascii = types.ModuleType("ubinascii")
        ubinascii.hexlify = lambda data: bytes(data)

        umqttsimple = types.ModuleType("umqttsimple")

        class MQTTException(Exception):
            pass

        umqttsimple.MQTTException = MQTTException
        umqttsimple.MQTTClient = MagicMock()

        stubs = {
            "machine": machine,
            "dht": dht,
            "network": network,
            "ujson": ujson,
            "ubinascii": ubinascii,
            "umqttsimple": umqttsimple,
            "time": time_mod,
        }

        sys.path.insert(0, str(RUTA_WOKWI))
        self._stub_keys = list(stubs)
        self._stub_prev = {k: sys.modules.get(k) for k in stubs}
        sys.modules.update(stubs)
        self.main = cargar_modulo("main", stubs)
        sys.path.remove(str(RUTA_WOKWI))

    def tearDown(self):
        for key in self._stub_keys:
            prev = self._stub_prev.get(key)
            if prev is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = prev

        # Reset del estado global del módulo bajo prueba
        self.main.mensajes_pendientes.clear()
        self.main.comandos_procesados.clear()
        self.main.cliente = None
        self.main.riego_fin = None
        self.main.riego_command_id = None

    def test_publicar_seguro_sin_cliente_guarda_pendiente(self):
        ok = self.main.publicar_seguro(
            self.main.TOPIC_ESTADO, {"device_id": "invernadero-01"}
        )
        self.assertFalse(ok)
        self.assertEqual(len(self.main.mensajes_pendientes), 1)

    def test_publicar_seguro_error_econnreset(self):
        cliente = MagicMock()
        cliente.publish.side_effect = OSError(104, "ECONNRESET")
        self.main.cliente = cliente

        ok = self.main.publicar_seguro(self.main.TOPIC_ESTADO, {})

        self.assertFalse(ok)
        self.assertIsNone(self.main.cliente)
        self.assertEqual(len(self.main.mensajes_pendientes), 1)

    def test_publicar_seguro_error_etimedout(self):
        cliente = MagicMock()
        cliente.publish.side_effect = OSError(110, "ETIMEDOUT")
        self.main.cliente = cliente

        ok = self.main.publicar_seguro(self.main.TOPIC_ESTADO, {})

        self.assertFalse(ok)
        self.assertIsNone(self.main.cliente)

    def test_publicar_seguro_ok_devuelve_true(self):
        cliente = MagicMock()
        self.main.cliente = cliente

        ok = self.main.publicar_seguro(self.main.TOPIC_SENSORES, {})

        self.assertTrue(ok)
        cliente.publish.assert_called_once()

    def test_enviar_pendientes_pop(self):
        cliente = MagicMock()
        self.main.cliente = cliente
        self.main.mensajes_pendientes.append(
            (self.main.TOPIC_ESTADO, {"device_id": "invernadero-01"})
        )

        self.main.enviar_pendientes()

        self.assertEqual(len(self.main.mensajes_pendientes), 0)
        cliente.publish.assert_called_once()

    def test_recibir_comando_duplicado(self):
        self.main.comandos_procesados.append("cmd-1")

        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar:
            self.main.recibir_comando(
                self.main.TOPIC_COMANDOS,
                json.dumps(
                    {
                        "command_id": "cmd-1",
                        self.KEY_ACTVADOR: "riego",
                        "accion": "PULSE",
                        "origen": "cloud",
                    }
                ).encode(),
            )

        mock_cambiar.assert_not_called()

    def test_recibir_comando_riego_valido(self):
        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar, patch.object(
            self.main, "publicar_estado"
        ), patch.object(
            self.main, "evento"
        ):
            self.main.recibir_comando(
                self.main.TOPIC_COMANDOS,
                json.dumps(
                    {
                        "command_id": "cmd-2",
                        self.KEY_ACTVADOR: "riego",
                        "accion": "PULSE",
                        "origen": "cloud",
                    }
                ).encode(),
            )

        self.assertTrue(mock_cambiar.called)
        self.assertIn("cmd-2", self.main.comandos_procesados)

    def test_main_executa_iteracao_sem_nameerror(self):
        """Ejecuta una iteración del loop principal con mocks y rompe el
        bucle con una excepción controlada. Detecta NameError por
        variables globales sin declarar 'global'."""

        class SalidaDelLoop(Exception):
            pass

        cliente_mock = MagicMock()
        cliente_mock.check_msg.side_effect = SalidaDelLoop("salida controlada")

        datos_sensores = {
            "device_id": "invernadero-01",
            "temperatura": 20.0,
            "humedad": 50.0,
            "luminosidad": 50.0,
        }

        nombre_wifi = [n for n in dir(self.main)
                       if n.startswith('con') and 'wifi' in n][0]
        nombre_mqtt = [n for n in dir(self.main)
                       if n.startswith('con') and 'mqtt' in n][0]

        with patch.object(
            self.main, 'leer_sensores', return_value=datos_sensores
        ), patch.object(
            self.main, nombre_wifi, return_value=True
        ), patch.object(
            self.main, nombre_mqtt, return_value=cliente_mock
        ), patch.object(
            self.main, 'publicar_seguro', return_value=True
        ):
            with self.assertRaises(SalidaDelLoop):
                self.main.main()

        self.assertIs(self.main.cliente, cliente_mock)

    def test_control_automatico_ventilacion(self):
        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar:
            self.main.control_automatico(
                {"temperatura": 35.0, "luminosidad": 50.0}
            )
            mock_cambiar.assert_any_call("ventilacion", 1)

        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar:
            self.main.control_automatico(
                {"temperatura": 27.0, "luminosidad": 50.0}
            )
            mock_cambiar.assert_any_call("ventilacion", 0)

    def test_control_automatico_iluminacion(self):
        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar:
            self.main.control_automatico(
                {"temperatura": 30.0, "luminosidad": 20.0}
            )
            mock_cambiar.assert_any_call("iluminacion", 1)

        with patch.object(
            self.main, "cambiar_estado"
        ) as mock_cambiar:
            self.main.control_automatico(
                {"temperatura": 30.0, "luminosidad": 50.0}
            )
            mock_cambiar.assert_any_call("iluminacion", 0)


if __name__ == "__main__":
    unittest.main()
