from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

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

    # Si la tabla ya existía sin la columna telefono, la agregamos ahora.
    cur.execute("PRAGMA table_info(movimientos)")
    columns = [row[1] for row in cur.fetchall()]
    if "telefono" not in columns:
        cur.execute("ALTER TABLE movimientos ADD COLUMN telefono TEXT")
        conn.commit()

    conn.close()

crear_tabla()

# ================= API =================

@app.route("/ventas")
def ventas():
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT id, fecha, cliente, telefono, monto, estado FROM movimientos")
        data = cur.fetchall()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/deudores")
def deudores():
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT id, fecha, cliente, telefono, monto, estado FROM movimientos WHERE estado='Pendiente' AND monto > 0")
        data = cur.fetchall()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/venta", methods=["POST"])
def nueva():
    try:
        d = request.json
        if not d or not all(k in d for k in ["fecha", "cliente", "telefono", "monto", "estado"]):
            return jsonify({"error": "Faltan campos requeridos"}), 400
        if not isinstance(d["monto"], (int, float)) or d["monto"] <= 0:
            return jsonify({"error": "Monto debe ser un número positivo"}), 400
        if not d["telefono"] or not isinstance(d["telefono"], str):
            return jsonify({"error": "Teléfono inválido"}), 400

        conn = conectar()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO movimientos (fecha, cliente, telefono, monto, estado) VALUES (?, ?, ?, ?, ?)",
            (d["fecha"], d["cliente"], d["telefono"], d["monto"], d["estado"])
        )
        conn.commit()
        conn.close()
        return jsonify({"ok": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pago_parcial/<int:id>", methods=["POST"])
def pago_parcial(id):
    try:
        data = request.json
        if not data or "monto" not in data:
            return jsonify({"error": "Falta monto"}), 400
        pago = data["monto"]
        if not isinstance(pago, (int, float)) or pago <= 0:
            return jsonify({"error": "Monto debe ser positivo"}), 400

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
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/total_hoy")
def total_hoy():
    try:
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT SUM(monto) FROM movimientos WHERE fecha=? AND estado='Pagado'", (hoy,))
        row = cur.fetchone()
        total = row[0] if row and row[0] else 0
        conn.close()
        return jsonify({"total": total}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/eliminar/<int:id>", methods=["DELETE", "POST"])
def eliminar(id):
    try:
        conn = conectar()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM movimientos WHERE id=?", (id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "Movimiento no encontrado"}), 404
        
        cur.execute("DELETE FROM movimientos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= WEB =================

@app.route("/")
def inicio():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>MARIA PAZ by CHARA SHOWROOM</title>
<style>
body { font-family: Arial; background:#111; color:white; text-align:center; }
input, button { padding:10px; margin:5px; border-radius:5px; border:none; }
button { background:#00c853; color:white; font-weight:bold; cursor:pointer; }
table { width:100%; margin-top:20px; border-collapse:collapse; }
th, td { padding:10px; border-bottom:1px solid #444; }
.deuda { background:#ff5252; }
</style>
</head>
<body>

<h1>💰 MARIA PAZ by CHARA SHOWROOM</h1>

<input id="cliente" placeholder="Cliente">
<input id="telefono" placeholder="Teléfono (sin 0 ni 15)">
<input id="monto" placeholder="Monto">

<br>

<button onclick="venta('contado')">💵 CONTADO</button>
<button onclick="venta('cuenta')">📒 CUENTA</button>
<button onclick="cargar()">🔄 ACTUALIZAR</button>

<h2 id="total"></h2>

<h3>📊 VENTAS</h3>
<table>
<thead>
<tr><th>ID</th><th>Fecha</th><th>Cliente</th><th>Tel</th><th>Monto</th><th>Estado</th><th>Acciones</th></tr>
</thead>
<tbody id="tabla"></tbody>
</table>

<h3>📒 DEUDORES</h3>
<button onclick="recordarTodos()">📲 Recordar a TODOS</button>

<table>
<thead>
<tr><th>Cliente</th><th>Debe</th><th>Acciones</th></tr>
</thead>
<tbody id="deudores"></tbody>
</table>

<script>

function venta(tipo){
    let cliente = document.getElementById("cliente").value.trim();
    let tel = document.getElementById("telefono").value.trim();
    let monto = parseFloat(document.getElementById("monto").value);

    if (!tel) return alert("Poné un teléfono válido");
    if (!monto || isNaN(monto) || monto <= 0) return alert("Poné un monto válido");
    if (tipo === "cuenta" && !cliente) return alert("Poné el nombre del cliente para CUENTA");

    fetch("/venta", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            fecha: new Date().toISOString().slice(0,10),
            cliente: tipo=== "cuenta" ? cliente : "",
            telefono: tel,
            monto: monto,
            estado: tipo==="contado" ? "Pagado" : "Pendiente"
        })
    })
    .then(r => {
        if (!r.ok) return r.json().then(err => Promise.reject(err.error || 'Error al guardar'));
        return r.json();
    })
    .then(()=>{
        document.getElementById("cliente").value = "";
        document.getElementById("telefono").value = "";
        document.getElementById("monto").value = "";
        cargar();
    })
    .catch(e => alert("❌ " + e));
}

function eliminar(id){
    if(confirm("¿Estás seguro que querés eliminar este registro?")){
        fetch("/eliminar/"+id, {
            method:"POST"
        })
        .then(r => {
            if (!r.ok) return r.json().then(err => Promise.reject(err.error || 'Error al eliminar'));
            return r.json();
        })
        .then(() => cargar())
        .catch(e => alert("❌ " + e));
    }
}

function cargar(){
    fetch("/ventas")
    .then(r=>r.json())
    .then(data=>{
        let html="";
        data.forEach(r=>{
            html+=`<tr>
                <td>${r[0]}</td>
                <td>${r[1]}</td>
                <td>${r[2]}</td>
                <td>${r[3]}</td>
                <td>$${r[4]}</td>
                <td>${r[5]}</td>
                <td><button onclick="eliminar(${r[0]})" style="background:#ff5252; padding:5px 10px;">❌ X</button></td>
            </tr>`;
        });
        document.getElementById("tabla").innerHTML=html;
    });

    fetch("/deudores")
    .then(r=>r.json())
    .then(data=>{
        let html="";
        data.forEach(r=>{
            let mensaje = `Hola ${r[2]} 😊
Te escribo de MARIA PAZ by CHARA SHOWROOM.
Tenés un saldo pendiente de $${r[4]}.
Cuando puedas coordinamos el pago 🙌`;

            let link = `https://wa.me/54${r[3]}?text=${encodeURIComponent(mensaje)}`;

            html+=`<tr class="deuda">
                <td>${r[2]}</td>
                <td>$${r[4]}</td>
                <td>
                    <button onclick="pagar(${r[0]})">✔ Pagar</button>
                    <button onclick="parcial(${r[0]})">💸 Parcial</button>
                    <a href="${link}" target="_blank">
                        <button>📲 Recordar</button>
                    </a>
                    <button onclick="eliminar(${r[0]})" style="background:#ff5252;">❌ X</button>
                </td>
            </tr>`;
        });
        document.getElementById("deudores").innerHTML=html;
    });

    fetch("/total_hoy")
    .then(r=>r.json())
    .then(d=>{
        document.getElementById("total").innerText = "Hoy: $" + d.total;
    });
}

function pagar(id){
    fetch("/pago_parcial/"+id, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({monto:999999})
    }).then(()=>cargar());
}

function parcial(id){
    let monto = prompt("¿Cuánto pagó?");
    if(!monto) return;

    fetch("/pago_parcial/"+id, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({monto: parseFloat(monto)})
    }).then(()=>cargar());
}

function recordarTodos(){
    fetch("/deudores")
    .then(r=>r.json())
    .then(data=>{
        if(data.length === 0){
            alert("No hay deudores");
            return;
        }

        let i = 0;

        function abrirSiguiente(){
            if(i >= data.length) return;

            let r = data[i];

            let mensaje = `Hola ${r[2]} 😊
Te escribo de MARIA PAZ by CHARA SHOWROOM.
Tenés un saldo pendiente de $${r[4]}.
Cuando puedas coordinamos el pago 🙌`;

            let link = `https://wa.me/54${r[3]}?text=${encodeURIComponent(mensaje)}`;

            window.open(link, "_blank");

            i++;
            setTimeout(abrirSiguiente, 2000);
        }

        abrirSiguiente();
    });
}

cargar();

</script>

</body>
</html>
""")

# =======================

app.run(host="0.0.0.0", port=5000)