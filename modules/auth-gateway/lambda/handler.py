import json
import os
import boto3

cog = boto3.client("cognito-idp")
USER_POOL_ID = os.environ["USER_POOL_ID"]
CLIENT_ID    = os.environ["CLIENT_ID"]


def _resp(status, body):
    return {"statusCode": status, "headers": {"Content-Type":"application/json"}, "body": json.dumps(body)}


def signup(body):
    # Expected: { "email": "...", "password": "...", "attributes": {"name":"..."} }
    attrs = [{"Name":"email","Value": body["email"]}]
    for k,v in (body.get("attributes") or {}).items():
        if k != "email":
            attrs.append({"Name": k, "Value": str(v)})

    cog.sign_up(
        ClientId=CLIENT_ID,
        Username=body["email"],
        Password=body["password"],
        UserAttributes=attrs
    )
    # Cognito sends verification email automatically (auto_verified_attributes=email)
    return _resp(200, {"message":"Sign-up successful. Check your email for the confirmation code."})


def confirm(body):
    # Expected: { "email": "...", "code": "123456" }
    cog.confirm_sign_up(ClientId=CLIENT_ID, Username=body["email"], ConfirmationCode=body["code"])
    return _resp(200, {"message":"Email confirmed."})


def resend(body):
    # Expected: { "email": "..." }
    cog.resend_confirmation_code(ClientId=CLIENT_ID, Username=body["email"])
    return _resp(200, {"message":"Confirmation code resent."})


def login(body):
    # Expected: { "email": "...", "password": "..." }
    r = cog.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": body["email"], "PASSWORD": body["password"]}
    )
    return _resp(200, {
        "access_token":  r["AuthenticationResult"]["AccessToken"],
        "id_token":      r["AuthenticationResult"]["IdToken"],
        "refresh_token": r["AuthenticationResult"].get("RefreshToken"),
        "expires_in":    r["AuthenticationResult"]["ExpiresIn"],
        "token_type":    r["AuthenticationResult"]["TokenType"]
    })


def refresh(body):
    # Expected: { "refresh_token": "..." }
    r = cog.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={"REFRESH_TOKEN": body["refresh_token"]}
    )
    return _resp(200, {
        "access_token": r["AuthenticationResult"]["AccessToken"],
        "id_token":     r["AuthenticationResult"]["IdToken"],
        "expires_in":   r["AuthenticationResult"]["ExpiresIn"],
        "token_type":   r["AuthenticationResult"]["TokenType"]
    })


def forgot(body):
    # Expected: { "email": "..." }
    cog.forgot_password(ClientId=CLIENT_ID, Username=body["email"])
    return _resp(200, {"message":"Password reset code sent to email."})


def reset(body):
    # Expected: { "email": "...", "code": "123456", "new_password": "..." }
    cog.confirm_forgot_password(
        ClientId=CLIENT_ID,
        Username=body["email"],
        ConfirmationCode=body["code"],
        Password=body["new_password"]
    )
    return _resp(200, {"message":"Password has been reset."})

ROUTES = {
    ("POST","/auth/signup"):  signup,
    ("POST","/auth/confirm"): confirm,
    ("POST","/auth/resend"):  resend,
    ("POST","/auth/login"):   login,
    ("POST","/auth/refresh"): refresh,
    ("POST","/auth/forgot"):  forgot,
    ("POST","/auth/reset"):   reset,
}


def lambda_handler(event, _context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    path   = event.get("requestContext", {}).get("http", {}).get("path")
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}

    handler = ROUTES.get((method, path))
    if not handler:
        return _resp(404, {"error":"Not found"})

    try:
        return handler(body)
    except cog.exceptions.UserNotConfirmedException:
        return _resp(400, {"error":"User not confirmed. Please verify your email."})
    except cog.exceptions.UsernameExistsException:
        return _resp(400, {"error":"User already exists."})
    except cog.exceptions.CodeMismatchException:
        return _resp(400, {"error":"Invalid confirmation code."})
    except cog.exceptions.ExpiredCodeException:
        return _resp(400, {"error":"Confirmation code expired."})
    except cog.exceptions.NotAuthorizedException as e:
        return _resp(401, {"error":"Invalid credentials."})
    except Exception as e:
        # Log the exception automatically via CloudWatch
        return _resp(500, {"error":"Internal server error"})
