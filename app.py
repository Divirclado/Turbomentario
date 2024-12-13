from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import sqlite3
import uuid

load_dotenv()

app = Flask(__name__, static_folder="back-end/static", template_folder="back-end/templates")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'comments.db')

# Crear directorios si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def moderate_text(text):
    # Implementar la función para moderar el contenido del texto
    return False

def init_db():
    """Inicializa la base de datos SQLite si no existe."""
    if not os.path.exists(DATABASE_FILE):
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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))

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

# Resto de las rutas y funciones se mantienen igual
# Usando DATABASE_FILE en lugar de repetir os.path.join para manejar la base de datos

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Inicializa tablas gestionadas por SQLAlchemy
        init_db()  # Inicializa la base de datos SQLite
    app.run(debug=True)
