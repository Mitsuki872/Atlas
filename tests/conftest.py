import os
import tempfile
os.environ['PROSPECT_DATA_DIR']=tempfile.mkdtemp(prefix='prospect-test-')
import pytest
from app.db import Base,engine,Session
from app.main import app,TOKEN
from fastapi.testclient import TestClient
@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    yield
@pytest.fixture
def client():
    with TestClient(app,headers={'X-Local-Token':TOKEN}) as c:yield c
