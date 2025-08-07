import json
import boto3
import os


def lambda_handler(event, context):
    bedrock_runtime = boto3.client("bedrock-runtime")
    
    # Define the model ID for Claude 3.5 Haiku
    inference_profile_arn = os.environ["INFERENCE_PROFILE_ARN"]
    
    # Extract the prompt from the event (e.g., from an API Gateway request)
    try:
        body = json.loads(event['body'])
        user_prompt = body.get('prompt', 'Hello, how are you?')
    except (json.JSONDecodeError, KeyError):
        user_prompt = 'Hello, how are you?' # Default prompt if parsing fails

    # Construct the messages payload for the Claude API
    messages = [
        {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
    ]

    # Invoke the model
    try:
        response = bedrock_runtime.invoke_model(
            modelId=inference_profile_arn,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": messages,
                "max_tokens": 500, # Adjust as needed
                "temperature": 0.7 # Adjust as needed
            })
        )

        response_body = json.loads(response['body'].read())
        assistant_response = response_body['content'][0]['text']

        return {
            'statusCode': 200,
            'body': json.dumps({'response': assistant_response})
        }

    except Exception as e:
        print(f"Error invoking model: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }