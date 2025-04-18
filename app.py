from flask import Flask, redirect, url_for
import os

app = Flask(__name__)
# Add a secret key for session management
app.secret_key = os.urandom(24)  # Generates a secure random key

# Importar las rutas después de inicializar la aplicación
import routes

# Redirigir la página de inicio a /login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)