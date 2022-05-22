from src.sio.client import Client
from src.api.firebase import Firebase

firebase = Firebase()

user = firebase.get_user(uid="C9F2dPOVa9SDt6XBPDuuqfzw3iB2")

print(user)


