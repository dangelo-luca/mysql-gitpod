import mysql.connector

import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database = "events"
)


mycursor = mydb.cursor()

mycursor.execute("CREATE DATABASE IF NOT EXISTS events")

mycursor.execute("SHOW DATABASES")


for x in mycursor:
  print(x)

mycursor.execute("CREATE TABLE IF NOT EXISTS customers (name VARCHAR(255), address VARCHAR(255))")
mycursor.execute("SHOW TABLES")

for x in mycursor:
  print(x)

mycursor.execute("SELECT * FROM customers")

myresult = mycursor.fetchall()

for x in myresult:
  print(x)