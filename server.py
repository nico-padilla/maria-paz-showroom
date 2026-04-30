from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# ================= BASE DE DATOS =================

def conectar():
    return sqlite3.connect("showroom.db")

def crear_tabla():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        cliente TEXT,
        telefono TEXT,
        monto REAL,
        estado TEXT
    )
    """)
    conn.commit()
    conn.close()

crear_tabla()

# ================= API =================

@app.route("/clientes")
def clientes():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT cliente, telefono, SUM(monto)
        FROM movimientos
        WHERE cliente != ''
        GROUP BY cliente, telefono
    """)
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/cliente/<nombre>")
def cliente(nombre):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM movimientos WHERE cliente=?", (nombre,))
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/venta", methods=["POST"])
def venta():
    d = request.json
    if not d or not all(k in d for k in ["fecha", "cliente", "telefono", "monto", "estado"]):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    try:
        monto = float(d["monto"])
    except (ValueError, TypeError):
        return jsonify({"error": "Monto inválido"}), 400

    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO movimientos (fecha, cliente, telefono, monto, estado) VALUES (?, ?, ?, ?, ?)",
        (d["fecha"], d["cliente"], d["telefono"], monto, d["estado"])
    )

    conn.commit()
    conn.close()
    return {"ok": True}

@app.route("/cuotas", methods=["POST"])
def cuotas():
    d = request.json
    if not d or not all(k in d for k in ["cliente", "telefono", "monto", "cuotas"]):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    try:
        total = float(d["monto"])
        cantidad = int(d["cuotas"])
    except (ValueError, TypeError):
        return jsonify({"error": "Monto o cuotas inválidos"}), 400

    cliente = d["cliente"]
    tel = d["telefono"]
    if cantidad <= 0:
        return jsonify({"error": "La cantidad de cuotas debe ser mayor a 0"}), 400

    valor = round(total / cantidad, 2)

    conn = conectar()
    cur = conn.cursor()

    for i in range(cantidad):
        fecha = (datetime.now() + timedelta(days=7*i)).strftime("%Y-%m-%d")
        cur.execute(
            "INSERT INTO movimientos (fecha, cliente, telefono, monto, estado) VALUES (?, ?, ?, ?, ?)",
            (fecha, cliente, tel, valor, "Pendiente")
        )

    conn.commit()
    conn.close()
    return {"ok": True}

@app.route("/pago_parcial/<int:id>", methods=["POST"])
def pago_parcial(id):
    data = request.json
    if not data or "monto" not in data:
        return jsonify({"error": "Falta monto"}), 400
    try:
        pago = float(data["monto"])
    except (ValueError, TypeError):
        return jsonify({"error": "Monto inválido"}), 400

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT monto FROM movimientos WHERE id=?", (id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Movimiento no encontrado"}), 404

    actual = row[0]
    nuevo = actual - pago

    if nuevo <= 0:
        cur.execute("UPDATE movimientos SET monto=0, estado='Pagado' WHERE id=?", (id,))
    else:
        cur.execute("UPDATE movimientos SET monto=? WHERE id=?", (nuevo, id))

    conn.commit()
    conn.close()
    return {"ok": True}

@app.route("/eliminar_antiguos", methods=["POST"])
def eliminar_antiguos():
    d = request.json
    if not d or "fecha" not in d:
        return jsonify({"error": "Falta fecha"}), 400
    try:
        cutoff = datetime.strptime(d["fecha"], "%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"error": "Formato de fecha inválido. Usa YYYY-MM-DD"}), 400

    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM movimientos WHERE fecha < ?", (d["fecha"],))
    eliminados = cur.rowcount
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "deleted": eliminados})

# ================= WEB =================

@app.route("/")
def inicio():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>MARIA PAZ by CHARA SHOWROOM</title>

<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body { font-family: Arial; background:#111; color:white; text-align:center; }
input, button { padding:10px; margin:5px; border-radius:5px; border:none; }
button { background:#00c853; color:white; font-weight:bold; cursor:pointer; }
table { width:100%; margin-top:20px; border-collapse:collapse; }
th, td { padding:10px; border-bottom:1px solid #444; }
.estado-pagado { color:#00e676; font-weight:bold; }
.estado-pendiente { color:#ff5252; font-weight:bold; }
</style>
</head>

<body>

<h1>💰 MARIA PAZ by CHARA SHOWROOM</h1>

<input id="cliente" placeholder="Cliente">
<input id="telefono" placeholder="Teléfono">
<input id="monto" placeholder="Monto">
<input id="cuotas" placeholder="Cuotas (ej: 4)">

<br>

<button onclick="contado()">💵 CONTADO</button>
<button onclick="cuenta()">📒 PAGAR</button>
<button onclick="crearCuotas()">📅 CUOTAS</button>
<br>
<input id="fecha_antigua" type="date" style="padding:10px; margin-top:10px;">
<button onclick="eliminarAntiguos()" style="background:#ff5252;">🗑️ Eliminar anteriores</button>

<h3>👥 CLIENTES</h3>
<table>
<thead>
<tr><th>Cliente</th><th>Total</th><th>Acciones</th></tr>
</thead>
<tbody id="clientes"></tbody>
</table>

<h3>📊 HISTORIAL</h3>
<table>
<thead>
<tr><th>Fecha</th><th>Monto</th><th>Estado</th><th>Acción</th></tr>
</thead>
<tbody id="historial"></tbody>
</table>

<button onclick="whatsapp()">📲 WhatsApp Cliente</button>

<script>

let clienteActual = "";
let telActual = "";

// ================= VENTAS =================

function contado(){ enviar("Pagado"); }
function cuenta(){ enviar("Pendiente"); }

function enviar(estado){
    let cliente = document.getElementById("cliente").value.trim();
    let telefono = document.getElementById("telefono").value.trim();
    let monto = parseFloat(document.getElementById("monto").value);

    if (!monto || isNaN(monto) || monto <= 0) return alert("Poné un monto válido");
    if (!telefono) return alert("Poné un teléfono válido");
    if (estado === "Pendiente" && !cliente) return alert("Poné el nombre del cliente para pagar en cuenta");

    fetch("/venta", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            fecha: new Date().toISOString().slice(0,10),
            cliente: cliente,
            telefono: telefono,
            monto: monto,
            estado: estado
        })
    }).then(()=>cargar());
}

// ================= CUOTAS =================

function crearCuotas(){
    fetch("/cuotas", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            cliente: document.getElementById("cliente").value,
            telefono: document.getElementById("telefono").value,
            monto: parseFloat(document.getElementById("monto").value),
            cuotas: document.getElementById("cuotas").value
        })
    }).then(()=>cargar());
}

// ================= CLIENTES =================

function cargar(){
    fetch("/clientes")
    .then(r=>r.json())
    .then(data=>{
        let html="";
        data.forEach(r=>{
            html+=`<tr>
                <td>${r[0]}</td>
                <td>$${r[2]}</td>
                <td><button onclick="ver('${r[0]}','${r[1]}')">Ver</button></td>
            </tr>`;
        });
        document.getElementById("clientes").innerHTML=html;
    });
}

// ================= HISTORIAL =================

function ver(nombre, tel){
    clienteActual = nombre;
    telActual = tel;

    fetch("/cliente/" + encodeURIComponent(nombre))
    .then(r=>r.json())
    .then(data=>{
        let html="";
        data.forEach(r=>{
            const estado = r[5] === 'Pagado' ?
                `<span class="estado-pagado">${r[5]}</span>` :
                `<span class="estado-pendiente">${r[5]}</span>`;
            html+=`<tr>
                <td>${r[1]}</td>
                <td>$${r[4]}</td>
                <td>${estado}</td>
                <td><button onclick="pagar(${r[0]})">✔</button></td>
            </tr>`;
        });
        document.getElementById("historial").innerHTML=html;
    });
}

// ================= PAGOS =================

function pagar(id){
    fetch("/pago_parcial/"+id,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({monto:999999})
    }).then(()=>ver(clienteActual, telActual));
}

// ================= WHATSAPP =================

function whatsapp(){
    if(!telActual) return alert("Seleccioná un cliente");

    let mensaje = `Hola ${clienteActual} 😊
Te escribo de MARIA PAZ by CHARA SHOWROOM.
Podés coordinar el pago de tu cuenta 🙌`;

    let link = `https://wa.me/54${telActual}?text=${encodeURIComponent(mensaje)}`;

    window.open(link, "_blank");
}

function eliminarAntiguos(){
    let fecha = document.getElementById("fecha_antigua").value;
    if(!fecha) return alert("Elegí una fecha para eliminar registros anteriores");
    if(!confirm(`Eliminar ventas anteriores a ${fecha} ?`)) return;

    fetch("/eliminar_antiguos", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({fecha: fecha})
    })
    .then(r => r.json())
    .then(data => {
        if(data.ok){
            alert(`Eliminados ${data.deleted} registros`);
            cargar();
        } else {
            alert("Error: " + (data.error || "No se pudo eliminar"));
        }
    })
    .catch(e => alert("Error: " + e));
}

// ================= INIT =================

cargar();

</script>

</body>
</html>
""")

# ================= RUN =================

app.run(host="0.0.0.0", port=5000)