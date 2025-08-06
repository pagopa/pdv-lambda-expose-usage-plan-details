import pytest
from unittest.mock import patch, MagicMock
import index

@pytest.fixture
def api_keys_response():
    return {
        "items": [
            {"id": "123abc", "name": "Key 1"},
            {"id": "456def", "name": "Key 2"}
        ]
    }

def test_list_api_keys_direct(api_keys_response):
    with patch("index.apigateway") as mock_apigateway:
        mock_apigateway.get_api_keys.return_value = api_keys_response
        response = index.list_api_keys()
        assert response.status_code == 200
        assert response.body == {"api_keys": [
            {"id": "123abc", "name": "Key 1"},
            {"id": "456def", "name": "Key 2"}
        ]}

def test_validate_api_key_success_direct():
    with patch("index.apigateway") as mock_apigateway, \
         patch.object(index.app, "current_event", create=True) as mock_event:
        mock_apigateway.get_api_key.return_value = {"value": "the-key-value"}
        mock_event.json_body = {"api_key_id": "123abc", "api_key_value": "the-key-value"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": True}

def test_validate_api_key_invalid_value_direct():
    with patch("index.apigateway") as mock_apigateway, \
         patch.object(index.app, "current_event", create=True) as mock_event:
        mock_apigateway.get_api_key.return_value = {"value": "the-key-value"}
        mock_event.json_body = {"api_key_id": "123abc", "api_key_value": "wrong-value"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": False}

def test_validate_api_key_not_found_direct():
    with patch("index.apigateway") as mock_apigateway, \
         patch.object(index.app, "current_event", create=True) as mock_event:
        class NotFoundException(Exception): pass
        mock_apigateway.get_api_key.side_effect = NotFoundException()
        mock_apigateway.exceptions = MagicMock()
        mock_apigateway.exceptions.NotFoundException = NotFoundException
        mock_event.json_body = {"api_key_id": "notfound", "api_key_value": "any"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": False}

def test_validate_api_key_missing_params_direct():
    with patch.object(index.app, "current_event", create=True) as mock_event:
        mock_event.json_body = {}
        response = index.validate_api_key()
        assert response.status_code == 400
        assert "api_key_id and api_key_value are required" in response.body["error"]