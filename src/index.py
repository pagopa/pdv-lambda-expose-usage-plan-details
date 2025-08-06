from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
import boto3
import os

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

AWS_REGION = os.getenv("AWS_REGION", "eu-south-1")

apigateway = boto3.client("apigateway", AWS_REGION)

@app.get("/api-keys")
@tracer.capture_method
def list_api_keys():
    response = apigateway.get_api_keys(includeValues=False)
    keys = [
        {"id": key["id"], "name": key.get("name", "")}
        for key in response.get("items", [])
    ]
    return Response(
        status_code=200,
        content_type="application/json",
        body={"api_keys": keys}
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