import mysql.connector

# Connessione iniziale senza database
mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database ="events"
)
mycursor = mydb.cursor()

def create_tables():
    # Crea il database se non esiste
    mycursor.execute("CREATE DATABASE IF NOT EXISTS events")

    # Seleziona il database appena creato
    mycursor.execute("USE events")

    # Crea la tabella users
    mycursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER NOT NULL AUTO_INCREMENT,
            username VARCHAR(80) NOT NULL,
            password VARCHAR(120) NOT NULL,
            created_at DATETIME,
            last_login DATETIME,
            is_active BOOLEAN,
            PRIMARY KEY (id),
            UNIQUE (username)
        );
    """)

    # Crea la tabella events
    mycursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER NOT NULL AUTO_INCREMENT,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            date DATE NOT NULL,
            location VARCHAR(200),
            coordinatex VARCHAR(500),
            coordinatey VARCHAR(500),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            tags VARCHAR(200),
            is_important BOOLEAN,
            images TEXT,
            created_by INTEGER,
            updated_by INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(updated_by) REFERENCES users(id)
        );
    """)

# Esegui la funzione per creare database e tabelle
create_tables()
