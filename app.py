from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import sqlite3
import uuid

# Cargar variables de entorno
load_dotenv()

# Configuración inicial de Flask
app = Flask(__name__, static_folder="back-end/static", template_folder="back-end/templates")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

# Configuración de la carpeta para subir archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ruta para la base de datos SQLite
DATABASE_FILE = os.path.join('/tmp', 'comments.db')

# Configuración de SQLAlchemy y LoginManager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Función para verificar extensiones permitidas
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para moderar texto (pendiente de implementación)
def moderate_text(text):
    # Implementar la función para moderar el contenido del texto
    return False

# Función para inicializar la base de datos
def init_db():
    # Crear el directorio si no existe
    db_directory = os.path.dirname(DATABASE_FILE)
    os.makedirs(db_directory, exist_ok=True)

    # Crear la base de datos y tabla de comentarios
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            text TEXT NOT NULL,
            media TEXT,
            likes INTEGER DEFAULT 0,
            parent_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Modelo de usuario
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Carga de usuario para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Manejo de usuarios no autorizados
@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))

# Rutas de la aplicación
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error durante el registro: {e}")
            flash('Hubo un problema al registrarte. Inténtalo de nuevo más tarde.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.password == password:
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Inicio de sesión no exitoso. Por favor verifica tu nombre de usuario y contraseña.', 'danger')
        except Exception as e:
            app.logger.error(f"Error durante el inicio de sesión: {e}")
            flash('Hubo un problema al iniciar sesión. Inténtalo de nuevo más tarde.', 'danger')
    return render_template('login.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/comments', methods=['POST'])
@login_required
def add_comment():
    username = current_user.username
    comment = request.form['comment']
    media = request.files.get('media')
    comment_id = str(uuid.uuid4())
    parent_id = request.form.get('parent_id')

    try:
        if moderate_text(comment):
            return jsonify({'success': False, 'error': 'Tu comentario contiene contenido inapropiado.'}), 400

        if media and not allowed_file(media.filename):
            return jsonify({'success': False, 'error': 'Tipo de archivo no permitido.'}), 400

        if media:
            media_path = os.path.join(UPLOAD_FOLDER, media.filename)
            media.save(media_path)
            media_url = f'/uploads/{media.filename}'
        else:
            media_url = None

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO comments (id, username, text, media, likes, parent_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (comment_id, username, comment, media_url, 0, parent_id))
        conn.commit()
        conn.close()

        comment_data = {
            'id': comment_id,
            'username': username,
            'text': comment,
            'media': media_url,
            'likes': 0,
            'parent_id': parent_id,
            'replies': []
        }
        return jsonify({'success': True, 'comment': comment_data})

    except Exception as e:
        app.logger.error(f"Error al añadir comentario: {e}")
        return jsonify({'success': False, 'error': 'Hubo un problema con el servidor. Por favor, inténtalo de nuevo más tarde.'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
