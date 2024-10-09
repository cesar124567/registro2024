from flask import Flask, render_template, request, redirect, url_for
import pyodbc
import face_recognition
import cv2
import numpy as np
from datetime import datetime  # Importar datetime

app = Flask(__name__)

# Conexión a la base de datos
def get_db_connection():
    conn = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\920220\OneDrive\Escritorio\admincontac.accdb;')
    return conn

# Función para capturar la imagen desde la cámara
def capturar_imagen():
    cap = cv2.VideoCapture(0)
    ret, imagen = cap.read()
    if not ret:
        print("No se pudo capturar la imagen desde la cámara.")
        cap.release()
        return None
    cap.release()
    return imagen

# Función para insertar una imagen en la base de datos
def guardar_imagen_bd(cursor, imagen, last_id):
    _, buffer = cv2.imencode('.jpg', imagen)
    imagen_blob = buffer.tobytes()
    
    print(f"Guardando imagen para ID: {last_id}")  # Imprimir para depuración
    cursor.execute("UPDATE [Lista de contactos] SET imagen = ? WHERE [Numero personal] = ?", (imagen_blob, last_id))

# Función para registrar el ingreso
def registrar_ingreso(nombre, codigo):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha y hora actual
    ahora = datetime.now()
    hora = ahora.strftime("%H:%M:%S")
    mes = ahora.strftime("%m")
    dia = ahora.strftime("%d")
    año = ahora.strftime("%Y")

    # Insertar en la tabla ingreso
    cursor.execute("INSERT INTO ingreso (Nombre, Codigo, Hora, Mes, Dia, Año) VALUES (?, ?, ?, ?, ?, ?)",
                   (nombre, codigo, hora, mes, dia, año))
    
    conn.commit()
    cursor.close()
    conn.close()

# Página de login para usuarios con reconocimiento facial
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        codigo = request.form.get("codigo")

        # Verificar credenciales en base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM [Lista de contactos] WHERE Nombre = ? AND Codigo = ?", (nombre, codigo))
        user = cursor.fetchone()

        if user:
            # Capturar imagen en vivo para verificación facial
            frame = capturar_imagen()
            if frame is None:
                return "Error al capturar imagen en vivo"

            # Obtener imagen de la base de datos (última imagen de usuario con el mismo código)
            cursor.execute("SELECT imagen FROM [Lista de contactos] WHERE Codigo = ?", (codigo,))
            imagen_blob = cursor.fetchone()

            if imagen_blob:
                imagen_referencia = np.frombuffer(imagen_blob[0], np.uint8)
                imagen_referencia = cv2.imdecode(imagen_referencia, cv2.IMREAD_COLOR)

                # Procesar ambas imágenes y comparar
                cod_referencia = face_recognition.face_encodings(imagen_referencia)
                cod_vivo = face_recognition.face_encodings(frame)

                if cod_referencia and cod_vivo and face_recognition.compare_faces([cod_referencia[0]], cod_vivo[0])[0]:
                    # Registrar ingreso
                    registrar_ingreso(nombre, codigo)
                    conn.close()
                    return redirect(url_for("success"))
                else:
                    conn.close()
                    return "Reconocimiento facial fallido. Persona no reconocida."
            else:
                conn.close()
                return "No se encontró imagen de referencia en la base de datos."
        else:
            conn.close()
            return "Código incorrecto o usuario no registrado."

    return render_template("registro.html")

# Página de éxito
@app.route("/success")
def success():
    return render_template("success.html")

# Página de administración
@app.route("/admon2024", methods=["GET", "POST"])
def admon():
    if request.method == "POST":
        codigo_unico = request.form.get("codigo_unico")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM [Administradores] WHERE Codigo = ?", (codigo_unico,))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            return redirect(url_for("accesosadm"))
        else:
            return "Código incorrecto o no autorizado"

    return render_template("admon2024.html")

# Página de registro de administradores con captura y almacenamiento de imagen
@app.route("/accesosadm", methods=["GET", "POST"])
def accesosadm():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        sexo = request.form.get("sexo")
        edad = request.form.get("edad")
        correo = request.form.get("correo")
        telefono = request.form.get("telefono")
        codigo = request.form.get("codigo")

        # Capturar la imagen para guardarla
        imagen = capturar_imagen()
        if imagen is None:
            return "Error al capturar la imagen"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar datos del usuario
        cursor.execute("INSERT INTO [Lista de contactos] (Nombre, Apellido, Sexo, Edad, Correo, Telefono, Codigo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (nombre, apellido, sexo, edad, correo, telefono, codigo))

        # Obtener el último ID insertado
        cursor.execute("SELECT @@IDENTITY")
        last_id = cursor.fetchone()[0]
        print(f"Último ID insertado: {last_id}")

        # Guardar la imagen en la misma línea
        guardar_imagen_bd(cursor, imagen, last_id)

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("success"))

    return render_template("accesosadm.html")

if __name__ == "__main__":
    app.run(debug=True)
