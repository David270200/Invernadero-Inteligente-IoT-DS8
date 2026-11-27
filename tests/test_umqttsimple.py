"""Tests para el cliente MQTT vendido wokwi/umqttsimple.py.

Simulan el socket para verificar que el packet CONNECT se forma
según MQTT 3.1.1 (nombre del protocolo).
"""

import importlib.util
import unittest
import unittest.mock as mock
from pathlib import Path

WOKWI = Path(__file__).resolve().parents[1] / "wokwi"
SPEC = importlib.util.spec_from_file_location(
    "umqttsimple", WOKWI / "umqttsimple.py"
)
umqttsimple = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(umqttsimple)


def parse_variable_header(packet):
    """Lee remaining length y protocol name, a la manera de un broker."""
    pos = 1
    length = 0
    shift = 0
    for _ in range(4):
        byte = packet[pos]
        pos += 1
        length |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    name_len = (packet[pos] << 8) | packet[pos + 1]
    name = packet[pos + 2 : pos + 2 + name_len]
    return length, name


class FakeSock:
    """Sockets MicroPython falsos que registran lo que se escribe."""

    def __init__(self):
        self.writes = []
        self.closed = False

    def settimeout(self, timeout):
        pass

    def setblocking(self, flag):
        pass

    def connect(self, address):
        self.writes.append(b"CONNECT")

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def read(self, count):
        return b""

    def close(self):
        self.closed = True


class TestEncodeLen(unittest.TestCase):
    def test_longitud_fija(self):
        buf = bytearray(b"\x00\x00\x00")
        i = umqttsimple._encode_len(buf, 128)
        self.assertEqual((i, buf[i]), (2, 1))

    def test_longitud_grande(self):
        buf = bytearray(b"\x00\x00\x00\x00")
        i = umqttsimple._encode_len(buf, 300)
        decodificado = (buf[1] & 0x7F) | (buf[2] << 7)
        self.assertEqual((i, decodificado), (2, 300))


class TestConnectPacket(unittest.TestCase):
    def test_packet_connect_es_valido_mqtt(self):
        fake = FakeSock()

        with mock.patch.object(
            umqttsimple.socket, "socket", return_value=fake
        ), mock.patch.object(
            umqttsimple.socket,
            "getaddrinfo",
            return_value=[("x", 1883, 0, 0, ("10.0.0.1", 1883))],
        ):
            cliente = umqttsimple.MQTTClient(
                b"greenhouse-test01", "broker.emqx.io", keepalive=60
            )
            with self.assertRaises(OSError):
                # CONNACK está stubeado a b"", así que connect falla
                # después de escribir el packet: iniciars esperamos eso.
                cliente.connect(timeout=3)

        packet = fake.writes[1:]
        self.assertGreater(len(packet), 1)
        length, name = parse_variable_header(b"".join(packet))
        self.assertEqual(name, b"MQTT")
        self.assertGreater(length, 0)


if __name__ == "__main__":
    unittest.main()
