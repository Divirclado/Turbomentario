from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import sqlite3
import uuid

load_dotenv()  # Cargar variables de entorno desde .env

app = Flask(__name__, static_folder="back-end/static", template_folder="back-end/templates")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'instance/users.db')}"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

def moderate_text(text):
    # Esta función verifica si el texto contiene palabras inapropiadas
    # y devuelve True si las contiene, False de lo contrario.
    inappropriate_words = ['funar', 'nojoda', 'verga']  # Lista de palabras inapropiadas
    for word in inappropriate_words:
        if word in text:
            return True
    return False

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

def init_db():
    with app.app_context():
        db.create_all()  # Crea todas las tablas definidas en los modelos de SQLAlchemy

    db_path = os.path.join(os.path.dirname(__file__), 'comments.db')  # Asegúrate de que la ruta es correcta
    conn = sqlite3.connect(db_path)
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

        db_path = os.path.join(os.path.dirname(__file__), 'comments.db')  # Asegúrate de que la ruta es correcta
        conn = sqlite3.connect(db_path)
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

@app.route('/api/comments', methods=['GET'])
@login_required
def get_comments():
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'comments.db')  # Asegúrate de que la ruta es correcta
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, text, media, likes, parent_id FROM comments')
        rows = cursor.fetchall()
        conn.close()

        comments = []
        comment_dict = {}
        for row in rows:
            comment = {
                'id': row[0],
                'username': row[1],
                'text': row[2],
                'media': row[3],
                'likes': row[4],
                'parent_id': row[5],
                'replies': []
            }
            comment_dict[comment['id']] = comment

        for comment in comment_dict.values():
            if comment['parent_id']:
                parent_comment = comment_dict.get(comment['parent_id'])
                if parent_comment:
                    parent_comment['replies'].append(comment)
            else:
                comments.append(comment)

        return jsonify(comments)

    except Exception as e:
        app.logger.error(f"Error al obtener comentarios: {e}")
        return jsonify({'success': False, 'error': 'Hubo un problema al obtener los comentarios. Por favor, inténtalo de nuevo más tarde.'}), 500

@app.route('/api/comments/<comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    db_path = os.path.join(os.path.dirname(__file__), 'back-end/comments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE comments SET likes = likes + 1 WHERE id = ?', (comment_id,))
    conn.commit()
    cursor.execute('SELECT likes FROM comments WHERE id = ?', (comment_id,))
    likes = cursor.fetchone()[0]
    conn.close()
    return jsonify({'success': True, 'likes': likes})

@app.route('/api/comments/<comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    db_path = os.path.join(os.path.dirname(__file__), 'back-end/comments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM comments WHERE id = ?', (comment_id,))
    row = cursor.fetchone()
    if row and row[0] == current_user.username:
        cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'success': False, 'error': 'No tienes permiso para eliminar este comentario.'}), 403

@app.route('/api/comments/<comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    new_text = request.form['text']
    db_path = os.path.join(os.path.dirname(__file__), 'back-end/comments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM comments WHERE id = ?', (comment_id,))
    row = cursor.fetchone()
    if row and row[0] == current_user.username:
        cursor.execute('UPDATE comments SET text = ? WHERE id = ?', (new_text, comment_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'success': False, 'error': 'No tienes permiso para editar este comentario.'}), 403

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
