from django.shortcuts import redirect
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.userprofile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return redirect('home')
        return wrapped_view
    return decorator
