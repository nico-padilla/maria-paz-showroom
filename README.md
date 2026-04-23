# 💰 MARIA PAZ by CHARA SHOWROOM

Sistema de gestión de ventas y cuentas para showroom. Permite registrar ventas al contado o de cuenta, y gestionar pagos y deudores.

## ✨ Características

- ✅ Registrar ventas al **CONTADO** o en **CUENTA**
- 📊 Tabla de ventas con historial completo
- 📒 Sección de deudores pendientes
- 💸 Pagos parciales y total
- 📱 Envío automático de recordatorios por WhatsApp
- 🗑️ Eliminar registros con confirmación
- 📈 Total de ventas del día (solo las pagadas)

## 🚀 Instalación

### Requisitos
- Python 3.x
- Flask
- SQLite3

### Pasos

1. Clona el repositorio:
```bash
git clone https://github.com/nico-padilla/maria-paz-showroom.git
cd maria-paz-showroom
```

2. Instala las dependencias:
```bash
pip install flask
```

3. Ejecuta el servidor:
```bash
python3 server.py
```

4. Abre en el navegador:
```
http://localhost:5000
```

## 💻 Uso

### Registrar una venta

1. Completa los campos:
   - **Cliente**: Nombre (solo para CUENTA)
   - **Teléfono**: Número sin 0 ni 15
   - **Monto**: Cantidad a registrar

2. Presiona **CONTADO** (pago inmediato) o **CUENTA** (venta fiada)

### Gestionar Deudores

- Ver todos los clientes con saldos pendientes
- **Pagar**: Marca como pagado completo
- **Parcial**: Realiza un pago parcial
- **Recordar**: Envía un mensaje por WhatsApp
- **Recordar a TODOS**: Envía recordatorio a todos los deudores
- **X**: Elimina el registro

### Eliminar Registros

Presiona **❌ X** en cualquier fila de ventas o deudores. Te pedirá confirmación antes de eliminar.

## 🗄️ Base de Datos

Usa SQLite3 con tabla `movimientos`:
- `id`: Identificador único
- `fecha`: Fecha de la venta
- `cliente`: Nombre del cliente (solo para cuentas)
- `telefono`: Teléfono de contacto
- `monto`: Monto registrado
- `estado`: "Pagado" o "Pendiente"

## 📂 Estructura

```
maria-paz-showroom/
├── server.py              # Servidor Flask
├── showroom.db            # Base de datos SQLite
├── Escritorio/
│   └── showroom.desktop   # Acceso directo para ejecutar
└── maria_paz_icon.svg     # Icono de la aplicación
```

## 🎨 Personalización

- Edita los textos en `server.py` en la sección HTML
- Cambia colores en el CSS
- Modifica el icono en `maria_paz_icon.svg`

## 📝 Licencia

Este proyecto es personal para MARIA PAZ by CHARA SHOWROOM.

---

Hecho con ❤️ por **nico**
