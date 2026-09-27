import os

import pyodbc
from dotenv import load_dotenv

load_dotenv()

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
driver = os.getenv("DB_DRIVER")

connection_string = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

connection = pyodbc.connect(
    connection_string,
    timeout=10,
)

cursor = connection.cursor()

cursor.execute("SELECT DB_NAME(), @@VERSION")

row = cursor.fetchone()

print("DATABASE CONNECTION SUCCESSFUL")
print("Database:", row[0])
print("SQL Server:", row[1].splitlines()[0])

cursor.close()
connection.close()