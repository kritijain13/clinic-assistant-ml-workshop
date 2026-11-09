from mcp_layer.database.connection import engine, Base
from mcp_layer.database.models import TokenUsage

Base.metadata.create_all(bind=engine)

print("Database connection successful.")
print("TokenUsage table created successfully.")