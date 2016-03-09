"""Basic User Class for Applications"""
from flask.ext.login import UserMixin

class User(UserMixin):

    def __init__(self, user_obj):
        self.username = None
        for key, value in user_obj.items():
            setattr(self, key, value)

    def get_id(self):
        if hasattr(self, 'username'):
            return self.username
        else:
            return None

    def is_active(self):
        return True

    def is_anonymouse(self):
        return False

    def is_authenticated(self):
        return True
