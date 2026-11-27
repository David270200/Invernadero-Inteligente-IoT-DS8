
import socket
import struct


class MQTTException(Exception):
    pass


def _encode_len(pkt, sz):
    i = 1

    while sz > 0x7F:
        pkt[i] = (sz & 0x7F) | 0x80
        sz >>= 7
        i += 1

    pkt[i] = sz

    return i


class MQTTClient:

    def __init__(
        self,
        client_id,
        server,
        port=0,
        user=None,
        password=None,
        keepalive=0,
        ssl=None,
        ssl_params=None,
    ):

        if port == 0:
            port = 8883 if ssl else 1883

        self.client_id = client_id
        self.sock = None
        self.server = server
        self.port = port
        self.ssl = ssl
        self.ssl_params = ssl_params or {}
        self.pid = 0
        self.cb = None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.timeout = 3

        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False

    def _write(self, datos):

        enviados = 0

        while enviados < len(datos):
            cantidad = self.sock.write(datos[enviados:])

            if not cantidad:
                raise OSError("Error enviando datos MQTT")

            enviados += cantidad

    def _read_exact(self, cantidad):

        datos = bytearray()

        while len(datos) < cantidad:

            parte = self.sock.read(cantidad - len(datos))

            if not parte:
                raise OSError("Conexion MQTT cerrada")

            datos.extend(parte)

        return bytes(datos)

    def _send_str(self, s):
        self._write(struct.pack("!H", len(s)))
        self._write(s)

    def _recv_len(self):

        n = 0
        sh = 0

        for _ in range(4):

            b = self._read_exact(1)[0]

            n |= (b & 0x7F) << sh

            if not b & 0x80:
                return n

            sh += 7

        raise MQTTException("Longitud MQTT invalida")

    def _next_pid(self):
        self.pid = (self.pid % 65535) + 1
        return self.pid

    def set_callback(self, f):
        self.cb = f

    def set_last_will(
        self, topic, msg, retain=False, qos=0
    ):

        assert 0 <= qos <= 2
        assert topic

        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True, timeout=3):

        self.timeout = timeout if timeout is not None else 3

        if self.sock:
            self.sock.close()

        self.sock = socket.socket()
        self.sock.settimeout(self.timeout)

        addr = socket.getaddrinfo(
            self.server, self.port
        )[0][-1]

        print("Direccion del broker:", addr)

        self.sock.connect(addr)

        print("Conexion TCP establecida")

        if self.ssl is True:

            import ssl

            self.sock = ssl.wrap_socket(
                self.sock, **self.ssl_params
            )

        elif self.ssl:

            self.sock = self.ssl.wrap_socket(
                self.sock,
                server_hostname=self.server
            )

        premsg = bytearray(b"\x10\0\0\0\0")

        # Cabecera correcta del protocolo MQTT 3.1.1.
        msg = bytearray(b"\x00\x04MQTT\x04\x02\0\0")

        sz = 10 + 2 + len(self.client_id)

        # Banderas de conexion.
        msg[7] = clean_session << 1

        if self.user:

            sz += 2 + len(self.user)

            msg[7] |= 0x80

            if self.pswd is not None:
                sz += 2 + len(self.pswd)
                msg[7] |= 0x40

        # Tiempo de mantenimiento de la conexion.
        if self.keepalive:

            assert self.keepalive < 65536

            msg[8] = self.keepalive >> 8
            msg[9] = self.keepalive & 0xFF

        if self.lw_topic:

            sz += (
                2 + len(self.lw_topic)
                + 2 + len(self.lw_msg)
            )

            msg[7] |= 0x04
            msg[7] |= self.lw_qos << 3
            msg[7] |= self.lw_retain << 5

        i = _encode_len(premsg, sz)

        self._write(premsg[:i + 1])
        self._write(msg)
        self._send_str(self.client_id)

        if self.lw_topic:
            self._send_str(self.lw_topic)
            self._send_str(self.lw_msg)

        if self.user:
            self._send_str(self.user)

            if self.pswd is not None:
                self._send_str(self.pswd)

        print("Paquete CONNECT enviado")
        print("Esperando respuesta CONNACK...")

        resp = self._read_exact(4)

        if resp[0] != 0x20 or resp[1] != 0x02:
            raise MQTTException("Respuesta MQTT invalida")

        if resp[3] != 0:
            raise MQTTException(resp[3])

        print("CONNACK recibido correctamente")

        return resp[2] & 1

    def disconnect(self):

        if self.sock:

            try:
                self._write(b"\xe0\0")

            finally:
                self.sock.close()
                self.sock = None

    def ping(self):
        self._write(b"\xc0\0")

    def publish(
        self, topic, msg, retain=False, qos=0
    ):

        assert qos in (0, 1)

        pkt = bytearray(b"\x30\0\0\0\0")

        pkt[0] |= qos << 1 | retain

        sz = 2 + len(topic) + len(msg)

        if qos:
            sz += 2

        i = _encode_len(pkt, sz)

        self._write(pkt[:i + 1])
        self._send_str(topic)

        if qos:

            pid = self._next_pid()

            self._write(struct.pack("!H", pid))

        self._write(msg)

        if qos == 1:

            while True:

                op = self.wait_msg()

                if op == 0x40:

                    sz = self._recv_len()

                    if sz != 2:
                        raise MQTTException("PUBACK invalido")

                    resp = self._read_exact(2)

                    rcv_pid = (resp[0] << 8) | resp[1]

                    if pid == rcv_pid:
                        return

    def subscribe(self, topic, qos=0):

        assert self.cb is not None

        pid = self._next_pid()

        pkt = bytearray(b"\x82\0\0\0\0")

        i = _encode_len(pkt, 5 + len(topic))

        self._write(pkt[:i + 1])
        self._write(struct.pack("!H", pid))
        self._send_str(topic)
        self._write(bytes((qos,)))

        while True:

            op = self.wait_msg()

            if op == 0x90:

                sz = self._recv_len()
                resp = self._read_exact(sz)

                if len(resp) < 3:
                    raise MQTTException("SUBACK invalido")

                rcv_pid = (resp[0] << 8) | resp[1]

                if rcv_pid != pid:
                    raise MQTTException("SUBACK incorrecto")

                if resp[2] == 0x80:
                    raise MQTTException("Suscripcion rechazada")

                print("Suscripcion MQTT confirmada:", topic)

                return

    def unsubscribe(self, topic):

        pid = self._next_pid()

        pkt = bytearray(b"\xa2\0\0\0\0")

        i = _encode_len(pkt, 4 + len(topic))

        self._write(pkt[:i + 1])
        self._write(struct.pack("!H", pid))
        self._send_str(topic)

        while True:

            op = self.wait_msg()

            if op == 0xB0:

                sz = self._recv_len()
                resp = self._read_exact(sz)

                if len(resp) == 2:
                    rcv_pid = (resp[0] << 8) | resp[1]

                    if rcv_pid == pid:
                        return

    def wait_msg(self, res=None):

        if res is None:
            res = self._read_exact(1)

        if res == b"":
            raise OSError("Conexion MQTT cerrada")

        op = res[0]

        if op == 0xD0:

            sz = self._recv_len()

            if sz != 0:
                raise MQTTException("PINGRESP invalido")

            return None

        if op & 0xF0 != 0x30:
            return op

        sz = self._recv_len()

        topic_len = self._read_exact(2)

        topic_len = (
            topic_len[0] << 8
        ) | topic_len[1]

        topic = self._read_exact(topic_len)

        sz -= topic_len + 2

        qos = (op >> 1) & 3

        if qos:

            pid_bytes = self._read_exact(2)

            pid = (
                pid_bytes[0] << 8
            ) | pid_bytes[1]

            sz -= 2

        if sz < 0:
            raise MQTTException("Mensaje MQTT invalido")

        msg = self._read_exact(sz)

        if self.cb:
            self.cb(topic, msg)

        if qos == 1:

            pkt = bytearray(b"\x40\x02\0\0")

            struct.pack_into("!H", pkt, 2, pid)

            self._write(pkt)

        elif qos > 1:
            raise MQTTException("QoS no soportado")

        return op

    def check_msg(self):

        self.sock.setblocking(False)

        try:

            try:
                res = self.sock.read(1)

            except OSError as error:

                if error.args and error.args[0] in (11, 35):
                    return None

                raise

        finally:

            self.sock.settimeout(self.timeout)

        if res is None:
            return None

        if res == b"":
            raise OSError("Conexion MQTT cerrada")

        return self.wait_msg(res)