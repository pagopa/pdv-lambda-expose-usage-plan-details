from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
import boto3
import os

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

AWS_REGION = os.getenv("AWS_REGION", "eu-south-1")
REST_API_ID = os.getenv("REST_API_ID")

apigateway = boto3.client("apigateway", AWS_REGION)

@app.get("/api-keys")
@tracer.capture_method
def list_api_keys():
    response = apigateway.get_api_keys(includeValues=False)
    filtered_keys = []
    for key in response.get("items", []):
        api_key_details = apigateway.get_api_key(apiKey=key["id"], includeValue=False)
        stage_keys = api_key_details.get("stageKeys", [])
        # Each stageKey is in the format "restApiId/stage"
        if any(sk.startswith(f"{REST_API_ID}/") for sk in stage_keys):
            filtered_keys.append({"id": key["id"], "name": key.get("name", "")})
    return Response(
        status_code=200,
        content_type="application/json",
        body={"api_keys": filtered_keys}
    )

@app.post("/validate-api-key")
@tracer.capture_method
def validate_api_key():
    body = app.current_event.json_body
    api_key_id = body.get("api_key_id")
    api_key_value = body.get("api_key_value")
    if not api_key_id or not api_key_value:
        return Response(
            status_code=400,
            content_type="application/json",
            body={"error": "api_key_id and api_key_value are required"}
        )
    try:
        api_key = apigateway.get_api_key(apiKey=api_key_id, includeValue=True)
        stage_keys = api_key.get("stageKeys", [])
        # Only consider the key if it belongs to the specified REST API
        if not any(sk.startswith(f"{REST_API_ID}/") for sk in stage_keys):
            valid = False
        else:
            stored_value = api_key.get("value")
            valid = stored_value == api_key_value
    except apigateway.exceptions.NotFoundException:
        valid = False
    return Response(
        status_code=200,
        content_type="application/json",
        body={"valid": valid}
    )

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    return app.resolve(event, context)