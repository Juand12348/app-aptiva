import os

# Las pruebas unitarias no deben tocar Neon: una URL falsa tiene prioridad sobre .env.
# El engine no se conecta hasta su primer uso, así que nunca se intenta abrir esta conexión.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
