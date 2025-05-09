from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.sqlite import TEXT

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, username, password=None):
        self.username = username
        if password:
            self.set_password(password)

    def set_password(self, password):
        """Hash e salva la password"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se la password corrisponde all'hash"""
        return check_password_hash(self.password, password)

    def get_dict(self):
        """Restituisce i dati dell'utente come dizionario"""
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(TEXT, nullable=False)  # Contenuto HTML ricco
    date = db.Column(db.Date, nullable=False)  # Data dell'evento storico
    location = db.Column(db.String(200))  # Luogo dell'evento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = db.Column(db.String(200))  # Tags separati da virgola (es: "Brigate Rosse, Moro, rapimento")
    is_important = db.Column(db.Boolean, default=False)  # Evento particolarmente importante
    images = db.Column(db.Text)  # Percorsi delle immagini separati da virgola
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relazioni
    creator = db.relationship('User', foreign_keys=[created_by])
    updater = db.relationship('User', foreign_keys=[updated_by])

    def __init__(self, title, content, date, created_by, **kwargs):
        self.title = title
        self.content = content
        self.date = date
        self.created_by = created_by
        self.updated_by = created_by
        
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_dict(self, include_content=False):
        """Restituisce i dati dell'evento come dizionario"""
        result = {
            'id': self.id,
            'title': self.title,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': self.tags.split(',') if self.tags else [],
            'is_important': self.is_important,
            'images': self.images.split(',') if self.images else [],
            'created_by': self.creator.username if self.creator else None,
            'updated_by': self.updater.username if self.updater else None
        }
        
        if include_content:
            result['content'] = self.content or ''
            
        return result

    def update(self, data, updated_by=None):
        """Aggiorna i dati dell'evento"""
        for key, value in data.items():
            if hasattr(self, key):
                if key == 'tags' and isinstance(value, list):
                    setattr(self, key, ','.join(value))
                elif key == 'images' and isinstance(value, list):
                    setattr(self, key, ','.join(value))
                else:
                    setattr(self, key, value)
        
        if updated_by:
            self.updated_by = updated_by