class ActionException(Exception):
    """
    Exeption raised when an action can't be performed
    """


class FirebaseException(Exception):
    """
    Exception raised when something goes wrong with firebase
    """


class InvalidUsernameException(FirebaseException):
    """
    Exception raised when the username is invalid
    """


class BotCreationException(FirebaseException):
    """
    Exception raised when the creation of a bot fails
    """


class AuthException(Exception):
    """
    Exception raised when custom authentification fails
    """


class UserManagerException(Exception):
    """
    Exception raised when something goes wrong with the user manager
    """
