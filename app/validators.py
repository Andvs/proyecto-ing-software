# en usuarios/validators.py

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class MaxLengthValidator:
    def __init__(self, max_length=20):
        self.max_length = max_length

    def validate(self, contraseña, user=None):
        if len(contraseña) > self.max_length:
            raise ValidationError(
                _("Esta contraseña es demasiado larga. No debe contener más de %(max_length)d caracteres."),
                code='password_too_long',
                params={'max_length': self.max_length},
            )

    def get_help_text(self):
        return _(
            "Tu contraseña no debe contener más de %(max_length)d caracteres."
            % {'max_length': self.max_length}
        )