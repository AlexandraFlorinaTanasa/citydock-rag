import uuid

import requests

BASE_URL = "http://localhost:8080/v1"
HEADERS = {
    "Authorization": "Bearer test_key_123",
    "X-Request-ID": str(uuid.uuid4()),
    "X-Tenant-ID": "ph-balta-doamnei",
    "Content-Type": "application/json"
}

def test_health_check():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_query_exact_match_hint():
    payload = {
        "question": "Ce spune articolul 15 din Legea 31/1990?",
        "language": "ro",
        "namespaces": ["legea_31_1990"],
        "hint_article_number": "15",
        "include_answer": True
    }
    response = requests.post(f"{BASE_URL}/query", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    articles = [c["chunk"]["article_number"] for c in data["citations"]]
    assert "15" in articles

def test_no_hallucination_contract():
    payload = {
        "question": "Cine este președintele planetei Marte?",
        "language": "ro",
        "namespaces": ["legea_31_1990"],
        "include_answer": True
    }
    response = requests.post(f"{BASE_URL}/query", json=payload, headers=HEADERS)
    data = response.json()
    assert data["answer"] is None
    assert data["confidence"] == 0.0
    assert len(data["citations"]) == 0
