# auth/auth.py
# Словарь с паролями и ролями
PASSWORDS = {
    "admin": "admin",
    "user": "user"
}

# Словарь с авторизованными пользователями
AUTHORIZED_USERS = {}  # user_id: role

def check_password(user_id: int, password: str) -> str | None:
    """
    Проверяет пароль и сохраняет роль пользователя.
    Возвращает роль ('admin' или 'user') или None если пароль неверный.
    """
    role = PASSWORDS.get(password)
    if role:
        AUTHORIZED_USERS[user_id] = role
        return role
    return None

def get_role(user_id: int) -> str | None:
    """
    Возвращает роль пользователя по его user_id
    """
    return AUTHORIZED_USERS.get(user_id)
