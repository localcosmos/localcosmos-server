from django.contrib.auth import get_user_model

from rest_framework.authentication import BaseAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

class LCTokenAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        if not auth or auth[0].lower() != 'token':
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise AuthenticationFailed(msg)

        key = auth[1]

        try:
            token = Token.objects.get(key=key)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Invalid token')

        try:
            user = User.objects.get(pk=token.user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed('User inactive or deleted')

        
        if user.is_active == True:
            return (user, token)

        else:
            msg = 'User inactive.'
            raise AuthenticationFailed(msg)
