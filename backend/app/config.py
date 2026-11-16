import os

# Endereço do frontend em desenvolvimento (Vite)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Banco de dados (será usado no G-06)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gestar.db")