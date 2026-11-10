def panel_access(request):
    user=request.user
    if not user.is_authenticated:
        return {'show_panel':False}
    from .panel import managed
    return {'show_panel':user.is_staff or user.is_superuser or managed(user).exists()}
