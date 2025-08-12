resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.namespace}_lambda_exec_role_${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        Effect = "Allow",
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

data "archive_file" lambda_file {
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
  type        = "zip" 
}

resource "aws_lambda_function" "bedrock_handler" {
  function_name    = "${var.namespace}_bedrock_api_lambda_${var.environment}"
  filename         = data.archive_file.lambda_file.output_path
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_file.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      INFERENCE_PROFILE_ARN = "arn:aws:bedrock:us-east-1:380171316226:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0"
    }
  }
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.namespace}_bedrock_http_api_${var.environment}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.bedrock_handler.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "api_route" {
  api_id             = aws_apigatewayv2_api.http_api.id
  route_key          = "POST /generate"
  target             = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
  authorization_type = "JWT"
}

resource "aws_lambda_permission" "allow_api_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bedrock_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}
