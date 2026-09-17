import proxy_server


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise proxy_server.requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_resource_path_works_from_project_root():
    resource = proxy_server.resource_path("README.md")

    assert resource.endswith("README.md")


def test_index_route_renders_the_main_page():
    client = proxy_server.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "PoE Ladder Tracker" in page
    assert "Fetch Characters" in page


def test_popout_route_renders_the_popout_page():
    response = proxy_server.app.test_client().get("/popout.html")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Race Mode" in page


def test_static_route_serves_css():
    response = proxy_server.app.test_client().get("/static/style.css")

    assert response.status_code == 200
    assert "body" in response.get_data(as_text=True)


def test_get_access_token_uses_cached_value(monkeypatch):
    monkeypatch.setitem(proxy_server.token_cache, "cached-scope", {"access_token": "abc", "token_expiry": 9999999999})

    token = proxy_server.get_access_token("cached-scope")

    assert token == "abc"


def test_get_access_token_fetches_and_caches_new_token(monkeypatch):
    proxy_server.token_cache.clear()

    class FakeTokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "new-token", "expires_in": 3600}

    monkeypatch.setattr(proxy_server.requests, "post", lambda *args, **kwargs: FakeTokenResponse())

    token = proxy_server.get_access_token("service:leagues")

    assert token == "new-token"
    assert proxy_server.token_cache["service:leagues"]["access_token"] == "new-token"


def test_get_access_token_returns_none_on_request_error(monkeypatch):
    proxy_server.token_cache.clear()

    def raise_error(*args, **kwargs):
        raise proxy_server.requests.exceptions.RequestException("token failure")

    monkeypatch.setattr(proxy_server.requests, "post", raise_error)

    assert proxy_server.get_access_token("service:leagues") is None


def test_leagues_route_returns_configuration_error_when_credentials_are_placeholder():
    original_client_id = proxy_server.CLIENT_ID
    original_client_secret = proxy_server.CLIENT_SECRET

    try:
        proxy_server.CLIENT_ID = "your_client_id_here"
        proxy_server.CLIENT_SECRET = "your_client_secret_here"

        response = proxy_server.app.test_client().get("/leagues")

        assert response.status_code == 503
        payload = response.get_json()
        assert payload["error"] == "configuration_error"
        assert "GGG API credentials" in payload["message"]
    finally:
        proxy_server.CLIENT_ID = original_client_id
        proxy_server.CLIENT_SECRET = original_client_secret


def test_leagues_route_returns_success_when_configured(monkeypatch):
    monkeypatch.setattr(proxy_server, "CLIENT_ID", "client-id")
    monkeypatch.setattr(proxy_server, "CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(proxy_server, "get_access_token", lambda *args, **kwargs: "token")
    monkeypatch.setattr(proxy_server.requests, "get", lambda *args, **kwargs: FakeResponse(200, [{"id": "Affliction"}]))

    response = proxy_server.app.test_client().get("/leagues")

    assert response.status_code == 200
    assert response.get_json() == [{"id": "Affliction"}]


def test_public_ladder_route_returns_json_from_upstream(monkeypatch):
    fake_payload = {
        "entries": [
            {
                "rank": 1,
                "character": {
                    "name": "AlphaRunner",
                    "class": "Champion",
                    "level": 90,
                    "experience": 1000000,
                },
            }
        ]
    }
    monkeypatch.setattr(proxy_server.requests, "get", lambda *args, **kwargs: FakeResponse(200, fake_payload))

    response = proxy_server.app.test_client().get("/public-ladder/Affliction?limit=10&offset=0")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entries"][0]["character"]["name"] == "AlphaRunner"


def test_public_ladder_route_returns_500_when_upstream_request_fails(monkeypatch):
    def raise_error(*args, **kwargs):
        raise proxy_server.requests.exceptions.RequestException("upstream timeout")

    monkeypatch.setattr(proxy_server.requests, "get", raise_error)

    response = proxy_server.app.test_client().get("/public-ladder/Affliction?limit=10&offset=0")

    assert response.status_code == 500
    payload = response.get_json()
    assert "upstream timeout" in payload["error"]


def test_public_ladder_route_retries_after_rate_limit(monkeypatch):
    fake_responses = [
        FakeResponse(429, {"error": "rate limited"}, {"Retry-After": "0"}),
        FakeResponse(200, {"entries": [{"character": {"name": "AlphaRunner"}}]}),
    ]

    monkeypatch.setattr(proxy_server.time, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(proxy_server.requests, "get", lambda *args, **kwargs: fake_responses.pop(0))

    response = proxy_server.app.test_client().get("/public-ladder/Affliction?limit=10&offset=0")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entries"][0]["character"]["name"] == "AlphaRunner"


def test_ladder_route_returns_500_when_token_fetch_fails(monkeypatch):
    monkeypatch.setattr(proxy_server, "get_access_token", lambda *args, **kwargs: None)

    response = proxy_server.app.test_client().get("/ladder/Affliction")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"] == "Could not authenticate with GGG API"


def test_ladder_route_returns_success_when_authenticated(monkeypatch):
    monkeypatch.setattr(proxy_server, "get_access_token", lambda *args, **kwargs: "token")
    monkeypatch.setattr(proxy_server.requests, "get", lambda *args, **kwargs: FakeResponse(200, {"entries": [{"character": {"name": "AlphaRunner"}}]}))

    response = proxy_server.app.test_client().get("/ladder/Affliction?limit=10&offset=0")

    assert response.status_code == 200
    assert response.get_json()["entries"][0]["character"]["name"] == "AlphaRunner"


def test_ladder_route_retries_after_rate_limit(monkeypatch):
    fake_responses = [
        FakeResponse(429, {"error": "rate limited"}, {"Retry-After": "0"}),
        FakeResponse(200, {"entries": [{"character": {"name": "AlphaRunner"}}]}),
    ]

    monkeypatch.setattr(proxy_server, "get_access_token", lambda *args, **kwargs: "token")
    monkeypatch.setattr(proxy_server.time, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(proxy_server.requests, "get", lambda *args, **kwargs: fake_responses.pop(0))

    response = proxy_server.app.test_client().get("/ladder/Affliction?limit=10&offset=0")

    assert response.status_code == 200
    assert response.get_json()["entries"][0]["character"]["name"] == "AlphaRunner"
