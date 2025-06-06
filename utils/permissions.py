def is_manager(user):
    return any(role.name in ["Admin", "Mod"] for role in user.roles)
