locals {
    namespace   = "essay_sensei_ai"
    environment = "dev"
}

module auth_gateway {
    source      = "../../../modules/auth-gateway"

    namespace   = local.namespace
    environment = local.environment
}

module genai_gateway {
    source      = "../../../modules/genai-gateway"

    namespace   = local.namespace
    environment = local.environment

    cognito_user_pool_id        = module.auth_gateway.cognito_user_pool_id
    cognito_user_pool_client_id = module.auth_gateway.cognito_user_pool_client_id
}