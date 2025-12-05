from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Role


class UserCreationForm(UserCreationForm):
    """Form for creating new users."""
    email = forms.EmailField(required=True)
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone',
                 'employee_id', 'department', 'roles', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required
        self.fields['email'].required = True


class UserUpdateForm(UserChangeForm):
    """Form for updating users."""
    password = None  # Remove password field from update form
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone',
                 'employee_id', 'department', 'roles', 'is_active')


class RoleForm(forms.ModelForm):
    """Form for creating/updating roles."""
    permissions = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Role
        fields = ('name', 'description', 'permissions', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import Permission
        self.fields['permissions'].queryset = Permission.objects.all()


class PasswordChangeForm(forms.Form):
    """Form for password change."""
    old_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Current Password"
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="New Password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm New Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("New passwords don't match.")

        return cleaned_data
