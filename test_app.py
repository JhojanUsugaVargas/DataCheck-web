import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page_loads(client):
    """Verifica que la página de login carga correctamente."""
    rv = client.get('/login')
    assert rv.status_code == 200
    assert b'DataCheck' in rv.data

def test_api_health(client):
    """Verifica un endpoint de la API."""
    rv = client.get('/api/login') # Method not allowed if GET, but we check if it exists
    assert rv.status_code == 405 # Method Not Allowed is fine, it means the route exists
