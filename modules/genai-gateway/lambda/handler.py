import boto3
import json
import os

bedrock = boto3.client("bedrock-runtime")


def lambda_handler(event, context):
    body = json.loads(event["body"])
    prompt = body.get("prompt", "")
    model_id = os.environ["MODEL_ID"]

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 300
        }),
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return {
        "statusCode": 200,
        "body": json.dumps({"completion": result["completion"]})
    }
