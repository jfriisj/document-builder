from fastapi.testclient import TestClient

from hashoej_document_builder.web.app import app


client = TestClient(app)


def test_health_endpoint() -> None:
    assert app.title == "Document Builder"
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
