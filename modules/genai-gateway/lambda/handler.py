import json
import boto3
import os

SYSTEM_PROPMT = (
    "You are acting as a GRE grader. "
    "Your role is to evaluate GRE writing responses by assigning an appropriate score "
    "and providing constructive, insightful feedback. The feedback should mirror the style "
    "of official GRE scoring: objective, criteria-based, and focused on helping the writer "
    "understand their strengths and weaknesses, along with concrete steps for improvement."
)

PROMPT_TASK = '''
Evaluate my GRE essay and return the result strictly as JSON in this format:

{
  "score": <numeric score from 0 to 6 in half-point increments>,
  "overallFeedbacks": [
      "<strengths with reference to a specific example>", 
      "<weakness with reference to a specific example>",
      <concrete, actionable items the writer can take immediately>
  ],
  "sentenceSuggestions": [
    {
      "sentence": "<original sentence>",
      "sentence_index": <index of the sentence in the essay, starting from 0>,
      "suggestion": "<improved sentence>",
      "explanation": "<why this change improves the sentence>",
      "action_item": "<specific advice the writer can apply in future writing>"
    }
    ... (maximum 50 entries, typically 20 - 30)
  ]
}

# Scoring Guidelines
The Analytical Writing score ranges from 0 to 6 in half-point increments. Use the following criteria:
- **6 / 5.5**: direct engagement with the prompt; insightful, in-depth analysis of complex ideas; highly persuasive and fully developed arguments; well organized; varied sentence structures and precise vocabulary; superior grammar/usage with only minor errors.
- **5 / 4.5**: direct engagement with the prompt; generally thoughtful analysis; logically sound arguments with relevant examples; good organization; clear meaning; good grammar and sentence control with occasional minor errors.
- **4 / 3.5**: direct engagement with the prompt; competent analysis; adequately developed arguments; acceptable organization; meaning conveyed with sufficient clarity though noticeable errors may be present.
- **3 / 2.5**: direct engagement with the prompt; limited analysis or weak development; inconsistent or weak organization; grammar/usage errors that often reduce clarity.
- **2 / 1.5**: direct engagement with the prompt; serious weaknesses in analysis, development, or organization; frequent language errors that obscure meaning.
- **1 / 0.5**: direct engagement with the prompt but fundamentally deficient; incoherent, irrelevant, or severely underdeveloped content; pervasive and severe language errors.
- **0**: unscorable (off-topic, copied, non-English, or gibberish).
- **NS**: no response provided.

# Overall Feedbacks
- strengths: Explain a positive aspect of the essay and reference a specific example to illustrate why it applies.
- weakness: Explain a shortcoming of the essay and reference a specific example to illustrate why it applies.
- action_item: Suggest a concrete, actionable step the writer can take immediately (e.g., reorganizing paragraphs, refining the thesis, correcting grammar, or adding stronger evidence).

# Sentence Suggestions:
- Generate 10 - 20 of the most impactful revisions (out of a maximum of 50).
- For each suggestion, include:
  - sentence: the original sentence (exactly as written)
  - sentence_index: zero-based index of the sentence within the essay
  - suggestion: a revised sentence with improved grammar, clarity, or expression
  - explanation: an explanation of how the revision improves the sentence (e.g., stronger vocabulary, smoother flow, corrected grammar)
  - action_item: an action item the writer can generalize to future writing
Prioritize the sentences where revisions will lead to the greatest improvement in clarity, grammar, style, or overall effectiveness of the essay.
'''

PROMPT_CONTEXT = '''
See below for the given prompt and my answer.

# Prompt
{0}

# Answer
{1}
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
    user_prompt = PROMPT_TASK + PROMPT_CONTEXT.format(question['prompt'], answer)
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
                "max_tokens": 2048, # Adjust as needed
                "temperature": 0.7, # Adjust as needed
                "system": SYSTEM_PROPMT,
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