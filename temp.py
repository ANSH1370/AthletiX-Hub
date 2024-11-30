import pymysql

def get_db_connection():
    try:
        cnx = pymysql.connect(
            host="localhost",
            user="root",
            password="root",
            database="athletix_hub"
        )
        print("Connected to the database successfully.")
        return cnx
    except pymysql.MySQLError as err:
        print(f"Database connection failed: {err}")
        return None

get_db_connection()