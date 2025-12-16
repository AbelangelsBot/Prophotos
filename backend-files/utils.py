import jwt
from datetime import datetime, timedelta
from django.conf import settings

def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': getattr(user, 'username', ''),
        'admin': getattr(user, 'admin', False),
        'exp': datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRATION_HOURS),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Le token a expiré.")
    except jwt.InvalidTokenError:
        raise Exception("Le token est invalide.")
