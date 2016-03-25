"""Basic User Class for Applications"""
from flask.ext.login import UserMixin

class User(UserMixin):
    loaded_users = {}
    
    def __init__(self, user_obj={}):
        self.username = None
        for key, value in user_obj.items():
            setattr(self, key, value)
        self.id = self.username
        self.loaded_users[self.username] = user_obj
    
    def get_id(self):
        if hasattr(self, 'username'):
            return self.username
        else:
            return None
            
    def get_user_obj(self, user_id):
        if user_id in self.loaded_users.keys():
            return self.loaded_users[user_id]
        else:
            return None
           
    def del_user_obj(self, user_id):
        if user_id in self.loaded_users.keys():
            del self.loaded_users[user_id]
    
    def is_active(self):
        return True

    def is_anonymouse(self):
        return False

    def is_authenticated(self):
        return True
