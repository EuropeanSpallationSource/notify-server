from fastapi.testclient import TestClient


def test_health_check(client: TestClient, api_version):
    response = client.get(f"/api/{api_version}/-/health")
    assert response.status_code == 200
    assert response.text == "OK"
