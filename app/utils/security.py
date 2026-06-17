from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    return generate_password_hash(password, method="scrypt")


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)
