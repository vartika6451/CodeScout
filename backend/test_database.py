from app.services.database import get_connection


with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")

        result = cursor.fetchone()

        print("Database connected successfully!")
        print(result[0])