# reset_db.py
from backend.database import engine, Base

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
