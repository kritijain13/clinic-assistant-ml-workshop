from sqlalchemy import text

from clinic_assistant.database.connection import engine, logger


try:
    with engine.connect() as connection:

        connection.execute(text("SELECT 1"))

        logger.info("Clinic MySQL connection successful")

        print("MySQL connection successful!")


except Exception as e:

    logger.error(f"Clinic MySQL connection failed: {str(e)}")

    print("MySQL connection failed!")
    print(e)