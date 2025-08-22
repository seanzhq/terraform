import json
import boto3
import os
import re


PROMPT_TASK = '''
Evaluate my GRE essay and return the result strictly as JSON in this format:

{
  "score": <numeric score from 0 to 6 in half-point increments>,
  "overallFeedbacks": ["feedback_1", "feedback_2", ...],
  "sentenceSuggestions": [
    {
      "sentence": "original sentence",
      "suggestion": "improved version of the sentence",
      "sentence_index": <index of the sentence in the essay, starting from 0>
    },
    ...
  ]
}
'''

PROMPT_CONTEXT = '''
# Question
{0}

# Answer
{1}

# General Rules
- The essay response must directly address the given prompt. If the answer is only partially related or entirely off-topic, the score should be significantly reduced. In such cases, the lack of relevance must be explicitly noted and explained in the overall feedback section.

# Scoring Guidelines
The Analytical Writing score ranges from 0 to 6 in half-point increments. Use the following criteria:

- **6 / 5.5**: Insightful, in-depth analysis of complex ideas; highly persuasive and well-developed arguments; well organized; strong sentence variety and precise vocabulary; superior grammar/usage with only minor errors.
- **5 / 4.5**: Generally thoughtful analysis; logically sound arguments with appropriate examples; good organization; clear meaning; good control of grammar and sentence structure with minor errors.
- **4 / 3.5**: Competent analysis; adequately developed arguments; acceptable organization; clarity is adequate but may contain noticeable errors.
- **3 / 2.5**: Limited analysis; weak organization; weak grammar/usage control with errors that reduce clarity.
- **2 / 1.5**: Serious weaknesses in analysis, organization, or grammar/usage; frequent errors that obscure meaning.
- **1 / 0.5**: Fundamentally deficient; incoherent or irrelevant content; pervasive errors.
- **0**: Essay is unscorable (off-topic, copied, non-English, or gibberish).
- **NS**: No response provided.

# Feedback Requirements
- **overallFeedbacks**: Provide clear pros and cons, along with specific areas for improvement (content, structure, clarity, grammar, etc.).
- **sentenceSuggestions**: Generate up to 10 of the most impactful suggestions. Each entry must include:
  - The exact original sentence.
  - An improved version with more elegant expression, grammar corrections, or clarity improvements.
  - The zero-based index of the sentence within the essay.
'''


def lambda_handler(event, context):
    bedrock_runtime = boto3.client("bedrock-runtime")
    
    # Define the model ID for Claude 3.5 Haiku
    inference_profile_arn = os.environ["INFERENCE_PROFILE_ARN"]
    
    # Extract the prompt from the event (e.g., from an API Gateway request)
    try:
        body = json.loads(event['body'])
        question = body.get('question')
        answer = body.get('answer')
    except (json.JSONDecodeError, KeyError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }

    # Construct the messages payload for the Claude API
    user_prompt = PROMPT_TASK + PROMPT_CONTEXT.format(question, answer)
    print(f"Prompt: \n{user_prompt}")

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
                "max_tokens": 2000, # Adjust as needed
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