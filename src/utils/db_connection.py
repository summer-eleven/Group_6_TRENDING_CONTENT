import os

import pyodbc
from dotenv import load_dotenv


load_dotenv()


def get_connection():
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
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string,
        timeout=10,
    )


if __name__ == "__main__":
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT DB_NAME()")
    database_name = cursor.fetchone()[0]

    print("SQL Server connection successful")
    print("Connected database:", database_name)

    cursor.close()
    connection.close()