from flask import Flask, request, jsonify
from flask_cors import CORS
from extensions import db
from models import User, Event
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import uuid
import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database = "events"
)

mycursor = mydb.cursor()
mycursor.execute("CREATE DATABASE IF NOT EXISTS events")

mycursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	password VARCHAR(120) NOT NULL, 
	created_at DATETIME, 
	last_login DATETIME, 
	is_active BOOLEAN,  
	PRIMARY KEY (id), 
	UNIQUE (username));""")


mycursor.execute("""CREATE TABLE events (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT NOT NULL, 
	date DATE NOT NULL, 
	location VARCHAR(200), 
	created_at DATETIME, 
	updated_at DATETIME, 
	tags VARCHAR(200), 
	is_important BOOLEAN, 
	images TEXT, 
	created_by INTEGER, 
	updated_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id)
);""")


app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crea la cartella se non esiste
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CORS(app, resources={r"/*": {"origins": "*"}})  # Consenti tutte le origini

# Configurazione del database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Creazione database e utente demo
with app.app_context():
    db.create_all()
    if not User.query.first():
        admin = User(username="admin", password="admin123")
        db.session.add(admin)
        db.session.commit()
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Validazione base
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Dati mancanti"}), 400

    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        # Aggiorna last_login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Login riuscito",
            "user": user.get_dict()
        }), 200
    
    return jsonify({
        "success": False,
        "message": "Credenziali non valide"
    }), 401

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.get_dict() for user in users]), 200

# Endpoint per la gestione degli eventi
@app.route('/events', methods=['GET', 'POST'])
def handle_events():
    if request.method == 'GET':
        # Recupera tutti gli eventi ordinati per data
        events = Event.query.order_by(Event.date).all()
        return jsonify([event.get_dict() for event in events]), 200
    
    elif request.method == 'POST':
        # Crea un nuovo evento
        data = request.get_json()
        
        try:
            # Verifica che l'utente esista
            creator = User.query.get(data.get('created_by', 1))  # Default a admin (id=1)
            if not creator:
                return jsonify({
                    'success': False,
                    'message': 'Utente creatore non valido'
                }), 400
                
            new_event = Event(
                title=data['title'],
                content=data['content'],
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                created_by=creator.id,
                updated_by=creator.id,
                location=data.get('location', ''),
                tags=','.join(data.get('tags', [])),
                is_important=data.get('is_important', False),
                images=data.get('images', '')
            )
            db.session.add(new_event)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Evento creato con successo',
                'event': new_event.get_dict()
            }), 201
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Errore nella creazione dell\'evento: {str(e)}'
            }), 400

@app.route('/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'GET':
        return jsonify(event.get_dict(include_content=True)), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        try:
            # Verifica che l'utente che modifica esista
            updater = User.query.get(data.get('updated_by', 1))  # Default a admin (id=1)
            if not updater:
                return jsonify({
                    'success': False,
                    'message': 'Utente non valido'
                }), 400
                
            update_data = {
                'title': data.get('title', event.title),
                'content': data.get('content', event.content),
                'location': data.get('location', event.location),
                'tags': ','.join(data.get('tags', event.tags.split(','))) if 'tags' in data else event.tags,
                'is_important': data.get('is_important', event.is_important),
                'images': data.get('images', event.images),
                'updated_by': updater.id
            }
            
            if 'date' in data:
                update_data['date'] = datetime.strptime(data['date'], '%Y-%m-%d').date()
                
            event.update(update_data)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Evento aggiornato con successo',
                'event': event.get_dict()
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Errore nell\'aggiornamento dell\'evento: {str(e)}'
            }), 400
    
    elif request.method == 'DELETE':
        try:
            # Prima elimina le immagini associate
            if event.images:
                for image_path in event.images.split(','):
                    if os.path.exists(image_path):
                        os.remove(image_path)
            
            db.session.delete(event)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Evento eliminato con successo'
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Errore nell\'eliminazione dell\'evento: {str(e)}'
            }), 400

@app.route('/api/events', methods=['POST'])
def create_event_with_images():
    try:
        data = request.form
        images = request.files.getlist('images')
        
        # Verifica che l'utente esista
        creator = User.query.get(int(data.get('created_by', 1)))  # Default a admin (id=1)
        if not creator:
            return jsonify({
                'success': False,
                'message': 'Utente creatore non valido'
            }), 400

        image_paths = []
        
        # Elabora tutte le immagini caricate
        for image in images:
            if image and allowed_file(image.filename):
                # Genera un nome unico per il file
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(save_path)
                image_paths.append(f"/{UPLOAD_FOLDER}/{filename}")

        # Processa il contenuto HTML per sostituire i data URL con i percorsi dei file
        content = data['content']
        if content:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            for img in soup.find_all('img'):
                if img['src'].startswith('data:image'):
                    # Se è un'immagine embedded, salviamo nel filesystem
                    if images:  # Usa la prima immagine caricata
                        img['src'] = image_paths.pop(0)
                    else:
                        img.decompose()  # Rimuovi se non ci sono immagini caricate
            content = str(soup)

        # Crea un nuovo evento
        new_event = Event(
            title=data['title'],
            content=content,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            created_by=creator.id,
            updated_by=creator.id,
            location=data.get('location', ''),
            tags=data.get('tags', ''),
            is_important=data.get('is_important', 'false') == 'true',
            images=','.join(image_paths) if image_paths else None
        )
        
        db.session.add(new_event)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': 'Evento creato con successo!',
            'event': new_event.get_dict()
        }), 201

    except Exception as e:
        # Rollback in caso di errore
        if 'image_paths' in locals():
            for path in image_paths:
                try:
                    os.remove(path.lstrip('/'))
                except:
                    pass
        return jsonify({
            'success': False, 
            'message': f'Errore: {str(e)}'
        }), 500


@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'Nessun file caricato'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nessun file selezionato'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Genera un nome unico per il file
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            # Restituisci solo il percorso relativo
            return jsonify({
                'success': True,
                'imageUrl': f"/{UPLOAD_FOLDER}/{filename}"
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'message': f'Errore durante il caricamento: {str(e)}'}), 500
    
    return jsonify({'success': False, 'message': 'Tipo file non consentito'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)