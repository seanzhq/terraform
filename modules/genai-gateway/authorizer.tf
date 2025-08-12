data "aws_region" "current" {}

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

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.http_api.id
  authorizer_type  = "JWT"
  name             = "${var.namespace}_cognito_jwt_${var.environment}"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.client.id]
    issuer   = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.pool.id}"
  }
}
