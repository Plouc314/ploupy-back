from src.api import app
from src.firebase import Firebase
import src.users as users

Firebase.auth()

r = users.get_user(username="bob")
print(r)