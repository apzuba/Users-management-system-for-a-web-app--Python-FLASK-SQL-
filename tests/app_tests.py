# python3.6 -m "nose"

from nose.tools import *
from app import app

app.config['TESTING'] = True
web = app.test_client()

def test_index():
    rv = web.get('/', follow_redirects=True)
    assert_equal(rv.status_code, 200)

    rv = web.get('/hello', follow_redirects=True)
    assert_equal(rv.status_code, 404)

    rv = web.get('/game', follow_redirects=True)
    assert_equal(rv.status_code, 200)

    assert_in(b"Welcome to", rv.data)

def test_access_session(login):
    with login:
        login.post("/", data={"username": "Ad","password":"ad"})
        # session is still accessible
        assert session["user_id"] == 3




        

    # rv = web.post('/hello', follow_redirects=True, data=data)
    # assert_in(b"Zed", rv.data)
    # assert_in(b"Hola",rv.data)
