import os

# Las pruebas no deben tocar Neon: estos valores tienen prioridad sobre .env.
# El engine no se conecta hasta su primer uso, así que nunca se intenta abrir esta conexión.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-de-al-menos-32-caracteres"
