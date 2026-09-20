import re
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


User = get_user_model()

class PasswordValidator:

    def validate(self, password, user=None):
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("Password must contain at least one uppercase letter."), code='password_no_upper')
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("Password must contain at least one lowercase letter."), code='password_no_lower')
        if not re.search(r'[0-9]', password):
            raise ValidationError(_("Password must contain at least one numeric character."), code='password_no_int')
        if not re.search(r'[!@#$%&*,.?_\-]', password):
            raise ValidationError(_("Password must contain at least one special character."), code='password_no_symbol')

    def help_text(self):
        return _(
            "Password must contain at least 1 uppercase letter, 1 lowercase letter,"
            " 1 numeric character, and 1 special character."
            )

def validate_email(value):
    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError(_("A user with this email exists."))
    return value

