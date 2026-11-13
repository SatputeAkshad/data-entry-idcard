import os, tempfile
from pathlib import Path
import pytest
# Set before application imports; tests never use the owner's real local database.
TEST_ROOT=tempfile.TemporaryDirectory(prefix='idcs-tests-')
os.environ['IDCS_DATA_DIR']=TEST_ROOT.name

@pytest.fixture
def client():
    pytest.importorskip('fastapi'); pytest.importorskip('sqlalchemy'); pytest.importorskip('alembic')
    from alembic.config import Config
    from alembic import command
    from backend.app.config import initialize, token
    initialize(); command.upgrade(Config('backend/alembic.ini'),'head')
    from backend.app.db import Base, engine
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables): connection.execute(table.delete())
    from backend.app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app,base_url='http://127.0.0.1:8765') as c:
        assert c.post('/api/unlock',json={'token':token()}).status_code==200
        c.headers['x-idcs-request']='1'
        yield c

@pytest.fixture
def institution(client):
    response=client.post('/api/institutions',json={'name':'Test School','year':'2026','fields':[{'key':'full_name','label':'Name','required':True},{'key':'student_id','label':'ID','required':True},{'key':'class','label':'Class','type':'select','options':['1','2'],'repeat':True}]})
    assert response.status_code==200,response.text
    return response.json()
