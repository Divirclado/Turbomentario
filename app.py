from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import sqlite3
import uuid

app = Flask(__name__, static_folder="back-end/static", template_folder="back-end/templates")
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

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

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def moderate_text(text):
    prohibited_words = ['mala_palabra1', 'mala_palabra2']
    return any(word in text for word in prohibited_words)

def init_db():
    conn = sqlite3.connect('comments.db')
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

# Inicializa la base de datos al iniciar la aplicación
with app.app_context():
    db.create_all()
init_db()

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Inicio de sesión no exitoso. Por favor verifica tu nombre de usuario y contraseña.', 'danger')
    return render_template('login.html')

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

    conn = sqlite3.connect('comments.db')
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

@app.route('/api/comments', methods=['GET'])
@login_required
def get_comments():
    conn = sqlite3.connect('comments.db')
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

@app.route('/api/comments/<comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    conn = sqlite3.connect('comments.db')
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
    conn = sqlite3.connect('comments.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)