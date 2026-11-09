from clinic_assistant.database.connection import Base, engine
from clinic_assistant.database import models


from src.logger import get_logger


logger = get_logger(__name__)


try:

    Base.metadata.create_all(bind=engine)

    logger.info("Clinic database tables created successfully")

    print("Clinic database tables created successfully!")


except Exception as e:

    logger.error(f"Table creation failed: {str(e)}")

    print("Table creation failed!")
    print(e)