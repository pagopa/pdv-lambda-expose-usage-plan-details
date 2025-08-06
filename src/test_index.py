import pytest
from unittest.mock import patch, MagicMock
import index

@pytest.fixture
def usage_plans_response():
    return {
        "items": [
            {
                "id": "plan1",
                "apiStages": [{"apiId": "restapi123", "stage": "stage"}]
            },
            {
                "id": "plan2",
                "apiStages": [{"apiId": "otherapi", "stage": "stage"}]
            }
        ]
    }

@pytest.fixture
def usage_plan_keys_response():
    return {
        "items": [
            {"keyId": "123abc"},
            {"keyId": "456def"}
        ]
    }

@pytest.fixture
def api_key_details():
    def _details(apiKey, includeValue):
        if apiKey == "123abc":
            if includeValue:
                return {"id": "123abc", "name": "Key 1", "value": "the-key-value"}
            else:
                return {"id": "123abc", "name": "Key 1"}
        elif apiKey == "456def":
            if includeValue:
                return {"id": "456def", "name": "Key 2", "value": "the-key-value-2"}
            else:
                return {"id": "456def", "name": "Key 2"}
        else:
            return {}
    return _details

@pytest.fixture
def rest_api_id():
    return "restapi123"

def test_list_api_keys_direct(usage_plans_response, usage_plan_keys_response, api_key_details, rest_api_id):
    with patch("index.apigateway") as mock_apigateway, patch("index.REST_API_ID", rest_api_id):
        mock_apigateway.get_usage_plans.return_value = usage_plans_response

        # Only return keys for the relevant usage plan (plan1)
        def usage_plan_keys_side_effect(usagePlanId, limit):
            if usagePlanId == "plan1":
                return usage_plan_keys_response
            else:
                return {"items": []}
        mock_apigateway.get_usage_plan_keys.side_effect = usage_plan_keys_side_effect

        mock_apigateway.get_api_key.side_effect = api_key_details

        response = index.list_api_keys()
        assert response.status_code == 200
        assert response.body == {
            "api_keys": [
                {"id": "123abc", "name": "Key 1"},
                {"id": "456def", "name": "Key 2"}
            ]
        }

def test_validate_api_key_success_direct(usage_plans_response, usage_plan_keys_response, api_key_details, rest_api_id):
    with patch("index.apigateway") as mock_apigateway, \
         patch("index.REST_API_ID", rest_api_id), \
         patch.object(index.app, "current_event", create=True) as mock_event:
        # Setup mocks for usage plans and keys
        mock_apigateway.get_usage_plans.return_value = usage_plans_response
        mock_apigateway.get_usage_plan_keys.return_value = usage_plan_keys_response
        mock_apigateway.get_api_key.side_effect = api_key_details
        mock_event.json_body = {"api_key_id": "123abc", "api_key_value": "the-key-value"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": True}

def test_validate_api_key_invalid_value_direct(usage_plans_response, usage_plan_keys_response, api_key_details, rest_api_id):
    with patch("index.apigateway") as mock_apigateway, \
         patch("index.REST_API_ID", rest_api_id), \
         patch.object(index.app, "current_event", create=True) as mock_event:
        mock_apigateway.get_usage_plans.return_value = usage_plans_response
        mock_apigateway.get_usage_plan_keys.return_value = usage_plan_keys_response
        mock_apigateway.get_api_key.side_effect = api_key_details
        mock_event.json_body = {"api_key_id": "123abc", "api_key_value": "wrong-value"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": False}

def test_validate_api_key_not_in_usage_plan(usage_plans_response, usage_plan_keys_response, api_key_details, rest_api_id):
    with patch("index.apigateway") as mock_apigateway, \
         patch("index.REST_API_ID", rest_api_id), \
         patch.object(index.app, "current_event", create=True) as mock_event:
        # Remove the key from usage_plan_keys_response
        mock_apigateway.get_usage_plans.return_value = usage_plans_response
        mock_apigateway.get_usage_plan_keys.return_value = {"items": []}
        mock_apigateway.get_api_key.side_effect = api_key_details
        mock_event.json_body = {"api_key_id": "not-in-plan", "api_key_value": "any"}
        response = index.validate_api_key()
        assert response.status_code == 200
        assert response.body == {"valid": False}

def test_validate_api_key_not_found_direct(usage_plans_response, usage_plan_keys_response, rest_api_id):
    with patch("index.apigateway") as mock_apigateway, \
         patch("index.REST_API_ID", rest_api_id), \
         patch.object(index.app, "current_event", create=True) as mock_event:
        class NotFoundException(Exception): pass
        mock_apigateway.get_usage_plans.return_value = usage_plans_response
        mock_apigateway.get_usage_plan_keys.return_value = usage_plan_keys_response
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