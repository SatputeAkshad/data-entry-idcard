from alembic import context
from backend.app.config import initialize
from backend.app.db import Base, engine
initialize()
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction(): context.run_migrations()
