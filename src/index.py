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
    # 1. Get all usage plans
    usage_plans = apigateway.get_usage_plans(limit=500)
    relevant_plan_ids = []
    for plan in usage_plans.get("items", []):
        for api_stage in plan.get("apiStages", []):
            if api_stage.get("apiId") == REST_API_ID:
                relevant_plan_ids.append(plan["id"])
                break

    # 2. For each usage plan, get API keys
    api_key_ids = set()
    for plan_id in relevant_plan_ids:
        usage_plan_keys = apigateway.get_usage_plan_keys(usagePlanId=plan_id, limit=500)
        for item in usage_plan_keys.get("items", []):
            api_key_ids.add(item["keyId"])

    # 3. Fetch details for each API key
    api_keys = []
    for key_id in api_key_ids:
        api_key_details = apigateway.get_api_key(apiKey=key_id, includeValue=False)
        api_keys.append({
            "id": api_key_details["id"],
            "name": api_key_details.get("name", "")
        })

    return Response(
        status_code=200,
        content_type="application/json",
        body={"api_keys": api_keys}
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
        # 1. Find all usage plans for the REST API
        usage_plans = apigateway.get_usage_plans(limit=500)
        relevant_plan_ids = []
        for plan in usage_plans.get("items", []):
            for api_stage in plan.get("apiStages", []):
                if api_stage.get("apiId") == REST_API_ID:
                    relevant_plan_ids.append(plan["id"])
                    break

        # 2. Check if the API key is in any relevant usage plan
        found = False
        for plan_id in relevant_plan_ids:
            usage_plan_keys = apigateway.get_usage_plan_keys(usagePlanId=plan_id, limit=500)
            for item in usage_plan_keys.get("items", []):
                if item["keyId"] == api_key_id:
                    found = True
                    break
            if found:
                break

        if not found:
            return Response(
                status_code=200,
                content_type="application/json",
                body={"valid": False}
            )

        # 3. If found, check the value
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