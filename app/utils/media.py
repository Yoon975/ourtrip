from flask import url_for


def media_url(path):
    if not path:
        return None
    if str(path).startswith(("http://", "https://", "/")):
        return path
    return url_for("static", filename=str(path).replace("\\", "/"))
