resource "aws_cognito_user_pool" "pool" {
  name = "${var.namespace}_api_users_${var.environment}"
  schema {
    attribute_data_type      = "String"
    name                     = "email"
    required                 = true
    mutable                  = true
    string_attribute_constraints { 
        min_length = 5
        max_length = 2048
    }
  }
  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.namespace}_api_client_${var.environment}"
  user_pool_id = aws_cognito_user_pool.pool.id

  generate_secret = false
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
  supported_identity_providers  = ["COGNITO"]
  access_token_validity         = 60 # minutes
  id_token_validity             = 60
  refresh_token_validity        = 30 # days
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "random_id" "suffix" { byte_length = 3 }

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = "${replace(var.namespace, "_", "-")}-api-${random_id.suffix.hex}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.pool.id
}

# --- LAMBDA that handles all /auth/* endpoints ---
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.namespace}_auth_lambda_exec_role_${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Effect="Allow", Principal={ Service="lambda.amazonaws.com" }, Action="sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Effect="Allow", Action=[
          "logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"
        ], Resource="*" },
      { Effect="Allow", Action=[
          "cognito-idp:SignUp",
          "cognito-idp:ConfirmSignUp",
          "cognito-idp:ResendConfirmationCode",
          "cognito-idp:InitiateAuth",
          "cognito-idp:RespondToAuthChallenge",
          "cognito-idp:ForgotPassword",
          "cognito-idp:ConfirmForgotPassword",
          "cognito-idp:AdminCreateUser" # optional if you plan admin signups
        ], Resource="*" }
    ]
  })
}

data "archive_file" lambda_file {
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
  type        = "zip" 
}

resource "aws_lambda_function" "auth_handler" {
  function_name    = "${var.namespace}_auth_api_lambda_${var.environment}"
  filename         = data.archive_file.lambda_file.output_path
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_file.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      USER_POOL_ID = aws_cognito_user_pool.pool.id
      CLIENT_ID    = aws_cognito_user_pool_client.client.id
    }
  }
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.namespace}_auth_http_api_${var.environment}"
  protocol_type = "HTTP"
}

# Integration
resource "aws_apigatewayv2_integration" "auth_integration" {
  api_id                  = aws_apigatewayv2_api.http_api.id
  integration_type        = "AWS_PROXY"
  integration_uri         = aws_lambda_function.auth_handler.invoke_arn
  integration_method      = "POST"
  payload_format_version  = "2.0"
}

# Routes
resource "aws_apigatewayv2_route" "auth_signup" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/signup"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_confirm" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/confirm"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_login" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/login"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_refresh" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/refresh"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_resend" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/resend"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_forgot" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/forgot"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
resource "aws_apigatewayv2_route" "auth_reset" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /auth/reset"
  target    = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}

# Allow API Gateway to invoke the Lambda
resource "aws_lambda_permission" "allow_api_auth_invoke" {
  statement_id  = "AllowAPIGatewayInvokeAuth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
