import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

class Firebase:

    PATH_ACCOUNT_KEY = "data/service_account_key.json"
    URL_DATABASE = "https://ploupy-6550c-default-rtdb.europe-west1.firebasedatabase.app/"
    _initialized = False

    @classmethod
    def auth(cls):
        '''
        Authentificate to firebase
        Must be done before using firebase
        '''

        if cls._initialized:
            return
        cls._initialized = True

        cred = credentials.Certificate(cls.PATH_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred, {
            "databaseURL": cls.URL_DATABASE
        })