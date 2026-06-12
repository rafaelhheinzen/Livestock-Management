from database import search_user_by_name
from werkzeug.security import check_password_hash


def validate_login(username, password):
    user = search_user_by_name(username)
    if user is None:
        return False
    return check_password_hash(user["password"], password)