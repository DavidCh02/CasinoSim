from sqlalchemy import text
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from app import app
from database import get_db_session
from models import User
import os
import random
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import time

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('login.html', error="Por favor, complete todos los campos")

        try:
            with get_db_session() as conn:
                # First, let's check if the user exists
                check_user = text("SELECT * FROM users WHERE username = :username")
                user = conn.execute(check_user, {"username": username}).fetchone()
                
                # Debug print
                print(f"Checking user: {username}")
                print(f"User found: {user}")
                
                if user:
                    # Now check password
                    if user.password == password:
                        session['username'] = username
                        session['user_id'] = user.id
                        print(f"Login successful for user: {username}")
                        return redirect(url_for('profile'))
                    else:
                        print(f"Password mismatch for user: {username}")
                        return render_template('login.html', error="Contraseña incorrecta")
                else:
                    print(f"User not found: {username}")
                    return render_template('login.html', error="Usuario no encontrado")

        except Exception as e:
            print(f"Error de login detallado: {str(e)}")
            return render_template('login.html', error="Error al conectar con la base de datos")

    return render_template('login.html')

# Add this new route at the end of the file
@app.route('/check_users')
def check_users():
    try:
        with get_db_session() as conn:
            # Get all users and their details
            users = conn.execute(text("SELECT * FROM users")).fetchall()
            return jsonify([{
                'id': user.id if hasattr(user, 'id') else None,
                'username': user.username if hasattr(user, 'username') else None,
                'password': user.password if hasattr(user, 'password') else None,
                'avatar_url': user.avatar_url if hasattr(user, 'avatar_url') else None
            } for user in users])
    except Exception as e:
        return str(e)

# Modify the register route to include initial money values
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                return render_template('register.html', error="Por favor, complete todos los campos")

            avatar_number = random.randint(0, 8)
            avatar_url = f'/static/img/avatares/image ({avatar_number}).png'

            with get_db_session() as conn:
                # Verificar si el usuario ya existe
                check_user = text("SELECT * FROM users WHERE username = :username")
                result = conn.execute(check_user, {"username": username}).fetchone()

                if result:
                    return render_template('register.html', error="El nombre de usuario ya está en uso")

                # Insertar el nuevo usuario con dinero inicial
                insert_user = text("""
                    INSERT INTO users (username, password, avatar_url, dinero_efectivo, dinero_banco, fecha_creacion) 
                    VALUES (:username, :password, :avatar_url, :dinero_efectivo, :dinero_banco, :fecha_creacion) 
                    RETURNING id
                """)
                
                result = conn.execute(insert_user, {
                    "username": username,
                    "password": password,
                    "avatar_url": avatar_url,
                    "dinero_efectivo": 1000,  # Initial cash
                    "dinero_banco": 500,      # Initial bank money
                    "fecha_creacion": datetime.now()
                }).fetchone()
                
                # Crear facturas iniciales
                facturas_iniciales = [
                    ("luz", 50.00),
                    ("agua", 30.00),
                    ("vivienda", 100.00)
                ]
                
                for tipo, monto in facturas_iniciales:
                    fecha_vencimiento = datetime.now() + timedelta(days=30)
                    conn.execute(text("""
                        INSERT INTO facturas (user_id, tipo, monto, fecha_vencimiento)
                        VALUES (:user_id, :tipo, :monto, :fecha_vencimiento)
                    """), {
                        "user_id": result.id,
                        "tipo": tipo,
                        "monto": monto,
                        "fecha_vencimiento": fecha_vencimiento
                    })
                
                conn.commit()
                return redirect(url_for('login'))

        except Exception as e:
            print(f"Error al registrar: {e}")
            return render_template('register.html', error="Error al registrar usuario")

    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db_session() as conn:
            # Modified query to check payment time
            user_data = conn.execute(text("""
                WITH last_payments AS (
                    SELECT 
                        tipo,
                        MAX(fecha_pago) as ultimo_pago
                    FROM facturas
                    WHERE user_id = (SELECT id FROM users WHERE username = :username)
                    AND pagado = true
                    GROUP BY tipo
                )
                SELECT 
                    u.username, 
                    u.fecha_creacion, 
                    u.dinero_efectivo, 
                    u.dinero_banco, 
                    u.avatar_url,
                    COALESCE(MAX(CASE WHEN f.tipo = 'luz' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN f.monto END), 0) as factura_luz,
                    COALESCE(MAX(CASE WHEN f.tipo = 'agua' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN f.monto END), 0) as factura_agua,
                    COALESCE(MAX(CASE WHEN f.tipo = 'vivienda' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN f.monto END), 0) as factura_vivienda,
                    COALESCE(BOOL_OR(CASE WHEN f.tipo = 'luz' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN true END), false) as tiene_factura_luz,
                    COALESCE(BOOL_OR(CASE WHEN f.tipo = 'agua' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN true END), false) as tiene_factura_agua,
                    COALESCE(BOOL_OR(CASE WHEN f.tipo = 'vivienda' AND (f.pagado = false OR (lp.ultimo_pago < NOW() - INTERVAL '1 minute')) THEN true END), false) as tiene_factura_vivienda
                FROM users u
                LEFT JOIN facturas f ON f.user_id = u.id
                LEFT JOIN last_payments lp ON f.tipo = lp.tipo
                WHERE u.username = :username
                GROUP BY u.id, u.username, u.fecha_creacion, u.dinero_efectivo, u.dinero_banco, u.avatar_url
            """), {"username": session['username']}).fetchone()

            if not user_data:
                return redirect(url_for('login'))

            return render_template('profile.html',
                                username=user_data.username,
                                fecha_creacion=user_data.fecha_creacion.strftime("%d/%m/%Y"),
                                dinero_efectivo=user_data.dinero_efectivo,
                                dinero_banco=user_data.dinero_banco,
                                avatar_url=user_data.avatar_url,
                                factura_luz=user_data.factura_luz if user_data.tiene_factura_luz else "No hay factura pendiente",
                                factura_agua=user_data.factura_agua if user_data.tiene_factura_agua else "No hay factura pendiente",
                                factura_vivienda=user_data.factura_vivienda if user_data.tiene_factura_vivienda else "No hay factura pendiente",
                                tiene_factura_luz=user_data.tiene_factura_luz,
                                tiene_factura_agua=user_data.tiene_factura_agua,
                                tiene_factura_vivienda=user_data.tiene_factura_vivienda)

    except Exception as e:
        print(f"Error al cargar el perfil: {e}")
        return redirect(url_for('login'))

@app.route('/pagar_factura', methods=['POST'])
def pagar_factura():
    if 'username' not in session:
        return jsonify({'mensaje': 'Sesión no iniciada'}), 401

    data = request.get_json()
    tipo_factura = data.get('tipo')

    try:
        with get_db_session() as conn:
            # First, get the factura amount and check if user has enough money
            factura_info = conn.execute(text("""
                SELECT f.id, f.monto, u.id as user_id, u.dinero_efectivo 
                FROM facturas f
                JOIN users u ON u.id = f.user_id
                WHERE u.username = :username 
                AND f.tipo = :tipo 
                AND f.pagado = false
                LIMIT 1
            """), {
                "username": session['username'],
                "tipo": tipo_factura
            }).fetchone()

            if not factura_info:
                return jsonify({'mensaje': 'Factura no encontrada'}), 400

            if factura_info.dinero_efectivo < factura_info.monto:
                return jsonify({'mensaje': 'Fondos insuficientes'}), 400

            # Update user's money
            conn.execute(text("""
                UPDATE users 
                SET dinero_efectivo = dinero_efectivo - :monto
                WHERE id = :user_id
            """), {
                "monto": factura_info.monto,
                "user_id": factura_info.user_id
            })

            # Mark bill as paid
            conn.execute(text("""
                UPDATE facturas 
                SET pagado = true, fecha_pago = NOW()
                WHERE id = :factura_id
            """), {
                "factura_id": factura_info.id
            })

            conn.commit()
            return jsonify({'mensaje': 'Pago realizado con éxito'})

    except Exception as e:
        print(f"Error en pago de factura: {e}")
        return jsonify({'mensaje': 'Error al procesar el pago'}), 500

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Add these new routes
@app.route('/inicio')
def inicio():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('inicio.html')

@app.route('/casino')
def casino():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('casino.html')

@app.route('/trabajar')
def trabajar():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('trabajar.html')

@app.route('/banco')
def banco():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('banco.html')

@app.route('/tienda')
def tienda():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('tienda.html')