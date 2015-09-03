from django.forms import ModelForm
from django.core.mail import send_mail
from django.template import Context, loader
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

from .models import Team
from .util import email_token_generator


class UserForm(ModelForm):
    """
    The portion of the registration form which ends up in the 'User' model. Designed to be used in
    conjunction with TeamForm.
    As specifc fields are directly referred to, there's no advantage in using `get_user_model()`: This won't
    work with user models other than django.contrib.auth.models.User out-of-the-box.
    """

    class Meta:
        model = User
        fields = ['username', 'password', 'email']
        labels = {
            'username': _('Name'),
            'email': _('Formal email')
        }
        help_texts = {
            'username': None,
            'email': _('Your authorative contact address. It will be used sensitive requests, such as '
                       'password resets or prize pay-outs.')
        }

    def save(self, commit=True):
        """
        save() variant which always sets the user to inactive. It should stay that way until the email
        address is confirmed.
        """
        user = super().save(commit=False)
        user.is_active = False

        if commit:
            user.save()

        return user

    def send_confirmation_mail(self, request):
        """
        Sends an email containing the address confirmation link to the user associated with this form. As it
        requires a User instance, it should only be called after the object has initially been saved.

        Args:
            request: The HttpRequest from which this function is being called
        """
        context = Context({
            'competition_name': settings.COMPETITION_NAME,
            'protocol': 'https' if request.is_secure() else 'http',
            'host': get_current_site(request),
            'user': self.instance.pk,
            'token': email_token_generator.make_token(self.instance)
        })
        message = loader.get_template('confirmation_mail.txt').render(context)

        send_mail(settings.COMPETITION_NAME+' email confirmation', message, settings.DEFAULT_FROM_EMAIL,
                  [self.instance.email])


class TeamForm(ModelForm):
    """
    The portion of the registration form which ends up in the 'Team' model. Designed to be used in
    conjunction with UserForm.
    """

    class Meta:
        model = Team
        fields = ['informal_email', 'image', 'country']
        help_texts = {
            'informal_email': _("A less authorative contact address, e.g. your team's mailing list. It will "
                                "receive all relevant information for participants."),
            'image': _('Optional. Your logo or similar.'),
        }

    def save(self, user, commit=True):   # pylint: disable=arguments-differ
        """
        save() variant which takes as an additional parameter the user model to be associated with the team.
        """
        team = super().save(commit=False)
        team.user = user

        if commit:
            team.save()

        return team