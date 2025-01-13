from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django import forms
from .models import UserProfile


def validate_name(value):
    if not value.isalpha():
        raise ValidationError("Name should contain only alphabetic characters.")


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={
            'invalid': 'Enter a valid email address.',
            'required': 'This field is required.'
        }
    )
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[validate_name],
        error_messages={'required': 'Enter your first name.'}
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[validate_name],
        error_messages={'required': 'Enter your last name.'}
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={'required': 'Please select a role.'}
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$',
                message="Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, and one number."
            )
        ],
        error_messages={'required': 'Enter a password.'}
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm Password",
        error_messages={'required': 'Confirm your password.'}
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False 
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].validators = [
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message="Username can only contain letters, numbers, and underscores."
            )
        ]
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username or username.strip() == "":
            raise ValidationError("Username cannot be empty or contain only spaces.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already in use. Please choose a different one.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Enter a valid email address.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise ValidationError("Enter your first name.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise ValidationError("Enter your last name.")
        return last_name

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data
