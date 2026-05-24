from database.schema import Base
from sqlalchemy import create_engine

DATABASE_URL = "sqlite:///nexus_prompts.db"

def init_database():
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True para ver SQL en consola
    Base.metadata.create_all(engine)
    print("✅ Base de datos y tablas creadas correctamente.")
    return engine

if __name__ == "__main__":
    init_database()
