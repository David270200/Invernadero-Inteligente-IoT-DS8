
const $ = id => document.getElementById(id);

let estados = {};
let conectado = false;
let grafica = null;
let actualizando = false;
let enviando = false;
let avisoTimer;

function fecha(valor) {
    if (!valor) return "--";

    let texto = valor.replace(" ", "T");

    if (!/(Z|[+-]\d{2}:\d{2})$/.test(texto)) {
        texto += "Z";
    }

    return new Date(texto).toLocaleString("es-PA");
}

async function obtener(ruta) {
    const respuesta = await fetch(ruta, {cache: "no-store"});

    if (!respuesta.ok) {
        throw new Error("Error consultando " + ruta);
    }

    return respuesta.json();
}

function barra(id, valor) {
    $(id).style.width =
        Math.max(0, Math.min(100, valor)) + "%";
}

function notificar(mensaje) {
    const elemento = $("notificacion");

    elemento.textContent = mensaje;
    elemento.classList.add("visible");

    clearTimeout(avisoTimer);

    avisoTimer = setTimeout(() => {
        elemento.classList.remove("visible");
    }, 3500);
}

function mostrarLectura(datos) {
    if (!datos.timestamp) return;

    $("temperatura").textContent =
        Number(datos.temperatura).toFixed(1);

    $("humedad").textContent =
        Number(datos.humedad).toFixed(1);

    $("luminosidad").textContent =
        Number(datos.luminosidad).toFixed(1);

    barra("barra-temp", datos.temperatura / 80 * 100);
    barra("barra-hum", datos.humedad);
    barra("barra-luz", datos.luminosidad);

    $("alerta-temp").textContent =
        datos.temperatura > 30
            ? "Temperatura elevada"
            : "Temperatura dentro del umbral";

    $("alerta-luz").textContent =
        datos.luminosidad < 30
            ? "Luminosidad baja"
            : "Nivel de luz suficiente";

    $("actualizacion").textContent =
        "Última lectura: " + fecha(datos.timestamp);
}

function mostrarEstados(datos) {
    estados = datos;

    for (const actuador of Object.keys(datos)) {
        const estado = datos[actuador];
        const activo = estado === "ON";
        const conocido = estado === "ON" || estado === "OFF";

        $("estado-" + actuador).textContent =
            conocido
                ? activo ? "Encendido" : "Apagado"
                : "Sin confirmación";

        const boton = $("btn-" + actuador);

        boton.disabled = !conectado || enviando ||
            (actuador !== "riego" && !conocido) ||
            (actuador === "riego" && activo);

        if (actuador !== "riego") {
            boton.classList.toggle("on", activo);
            boton.setAttribute("aria-pressed", String(activo));
        }
    }
}

function mostrarEventos(eventos) {
    const tabla = $("tabla-eventos");
    tabla.replaceChildren();

    if (!eventos.length) {
        const fila = tabla.insertRow();
        const celda = fila.insertCell();
        celda.colSpan = 3;
        celda.textContent = "No hay eventos registrados.";
        return;
    }

    eventos.forEach(evento => {
        const fila = tabla.insertRow();

        [
            evento.tipo,
            evento.descripcion,
            fecha(evento.timestamp)
        ].forEach(valor => {
            fila.insertCell().textContent = valor;
        });
    });
}

function mostrarGrafica(lecturas) {
    if (!window.Chart) return;

    const etiquetas = lecturas.map(d => fecha(d.timestamp));

    const series = [
        {
            label: "Temperatura °C",
            data: lecturas.map(d => d.temperatura),
            borderColor: "#fb9a60",
            yAxisID: "temperatura"
        },
        {
            label: "Humedad %",
            data: lecturas.map(d => d.humedad),
            borderColor: "#65b6f8",
            yAxisID: "porcentaje"
        },
        {
            label: "Luminosidad %",
            data: lecturas.map(d => d.luminosidad),
            borderColor: "#f4ce62",
            yAxisID: "porcentaje"
        }
    ].map(serie => ({
        ...serie,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 0
    }));

    if (grafica) {
        grafica.data.labels = etiquetas;
        grafica.data.datasets = series;
        grafica.update("none");
        return;
    }

    grafica = new Chart($("grafica"), {
        type: "line",
        data: {
            labels: etiquetas,
            datasets: series
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#a8bfb0",
                        usePointStyle: true,
                        boxWidth: 8
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#91a99b",
                        maxTicksLimit: 5
                    },
                    grid: {display: false}
                },
                temperatura: {
                    position: "left",
                    ticks: {color: "#fb9a60"},
                    grid: {color: "#263a30"},
                    title: {
                        display: true,
                        text: "°C",
                        color: "#fb9a60"
                    }
                },
                porcentaje: {
                    position: "right",
                    min: 0,
                    max: 100,
                    ticks: {color: "#91a99b"},
                    grid: {drawOnChartArea: false},
                    title: {
                        display: true,
                        text: "%",
                        color: "#91a99b"
                    }
                }
            }
        }
    });
}

async function actualizar() {
    if (actualizando) return;
    actualizando = true;

    try {
        const [lectura, historial, estado, eventos, conexion] =
            await Promise.all([
                obtener("/api/actual"),
                obtener("/api/lecturas"),
                obtener("/api/estados"),
                obtener("/api/eventos"),
                obtener("/api/conexion")
            ]);

        conectado = conexion.mqtt;

        $("conexion").textContent =
            conectado ? "● MQTT conectado" : "● MQTT desconectado";

        $("conexion").className =
            "connection " + (conectado ? "online" : "offline");

        mostrarLectura(lectura);
        mostrarEstados(estado);
        mostrarEventos(eventos);
        mostrarGrafica(historial);

    } catch (error) {
        conectado = false;

        $("conexion").textContent = "● Error de conexión";
        $("conexion").className = "connection offline";

        ["ventilacion", "iluminacion", "riego"].forEach(a => {
            $("btn-" + a).disabled = true;
        });

        console.error(error);
    } finally {
        actualizando = false;
    }
}

async function enviarComando(actuador, accion) {
    if (!conectado || enviando) return;

    enviando = true;
    mostrarEstados(estados);

    try {
        const respuesta = await fetch("/api/comandos", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({actuador, accion})
        });

        if (!respuesta.ok) {
            throw new Error("No se pudo enviar el comando");
        }

        notificar("Comando enviado. Esperando confirmación.");

    } catch (error) {
        notificar(error.message);
    } finally {
        enviando = false;
        await actualizar();
    }
}

function alternar(actuador) {
    if (!["ON", "OFF"].includes(estados[actuador])) return;

    const accion = estados[actuador] === "ON" ? "OFF" : "ON";

    enviarComando(actuador, accion);
}

document.querySelectorAll("nav a").forEach(enlace => {
    enlace.addEventListener("click", () => {
        document.querySelectorAll("nav a").forEach(a => {
            a.classList.remove("active");
        });
        enlace.classList.add("active");
    });
});

actualizar();
setInterval(actualizar, 2000);