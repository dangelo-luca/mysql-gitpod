from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import mysql.connector
import os
import uuid
from bs4 import BeautifulSoup
from models import mydb, mycursor  # importa la connessione MySQL

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Connessione MySQL
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='events'
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Dati mancanti"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (data['username'],))
    user = cursor.fetchone()

    if user and check_password_hash(user['password'], data['password']):
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
        conn.commit()
        cursor.close()
        conn.close()
        user.pop('password')
        return jsonify({"success": True, "message": "Login riuscito", "user": user}), 200

    return jsonify({"success": False, "message": "Credenziali non valide"}), 401

@app.route('/users', methods=['GET'])
def get_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, last_login FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users), 200

@app.route('/events', methods=['GET'])
def get_events():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(events), 200

@app.route('/events', methods=['POST'])
def create_event():
    data = request.get_json()
    if not data.get('content'):
        return jsonify({"error": "Il campo 'content' è obbligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO events (title, content, date, created_by, updated_by, location, coordinatex, coordinatey, tags, is_important, images)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['title'],
            data['content'],
            data['date'],
            data.get('created_by', 1),
            data.get('created_by', 1),
            data.get('location', ''),
            data.get('coordinatex', ''),
            data.get('coordinatey', ''),
            ','.join(data.get('tags', [])),
            data.get('is_important', False),
            data.get('images', '')
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Evento creato con successo"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_event(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        cursor.close()
        conn.close()
        if event:
            return jsonify(event), 200
        return jsonify({"success": False, "message": "Evento non trovato"}), 404

    elif request.method == 'PUT':
        data = request.get_json()
        try:
            update_fields = {
                'title': data.get('title'),
                'content': data.get('content'),
                'location': data.get('location'),
                'coordinatex': data.get('coordinatex'),
                'coordinatey': data.get('coordinatey'),
                'date': data.get('date'),
                'tags': ','.join(data.get('tags', [])) if 'tags' in data else None,
                'is_important': data.get('is_important'),
                'images': data.get('images'),
                'updated_by': data.get('updated_by', 1)
            }

            updates = ", ".join([f"{k} = %s" for k in update_fields if update_fields[k] is not None])
            values = [v for v in update_fields.values() if v is not None] + [event_id]
            cursor.execute(f"UPDATE events SET {updates} WHERE id = %s", values)
            conn.commit()
            return jsonify({"success": True, "message": "Evento aggiornato"}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            cursor.close()
            conn.close()

    elif request.method == 'DELETE':
        try:
            cursor.execute("SELECT images FROM events WHERE id = %s", (event_id,))
            event = cursor.fetchone()
            if event and event['images']:
                for path in event['images'].split(','):
                    full_path = path.lstrip('/')
                    if os.path.exists(full_path):
                        os.remove(full_path)
            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
            conn.commit()
            return jsonify({"success": True, "message": "Evento eliminato"}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            cursor.close()
            conn.close()

@app.route('/api/events', methods=['POST'])
def create_event_with_images():
    try:
        data = request.form
        images = request.files.getlist('images')
        conn = get_connection()
        cursor = conn.cursor()

        image_paths = []
        for image in images:
            if image and allowed_file(image.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(save_path)
                image_paths.append(f"/{UPLOAD_FOLDER}/{filename}")

        content = data['content']
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            for img in soup.find_all('img'):
                if img['src'].startswith('data:image') and image_paths:
                    img['src'] = image_paths.pop(0)
                elif img['src'].startswith('data:image'):
                    img.decompose()
            content = str(soup)

        cursor.execute("""
            INSERT INTO events (title, content, date, created_by, updated_by, location, coordinatex, coordinatey, tags, is_important, images)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['title'],
            content,
            data['date'],
            data.get('created_by', 1),
            data.get('created_by', 1),
            data.get('location', ''),
            data.get('coordinatex', ''),
            data.get('coordinatey', ''),
            data.get('tags', ''),
            data.get('is_important', 'false') == 'true',
            ','.join(image_paths) if image_paths else None
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Evento creato con immagini"}), 201

    except Exception as e:
        if 'image_paths' in locals():
            for path in image_paths:
                try:
                    os.remove(path.lstrip('/'))
                except:
                    pass
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'Nessun file caricato'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nessun file selezionato'}), 400

    if file and allowed_file(file.filename):
        try:
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            return jsonify({'success': True, 'imageUrl': f"/{UPLOAD_FOLDER}/{filename}"}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

    return jsonify({'success': False, 'message': 'Tipo file non consentito'}), 400

@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
