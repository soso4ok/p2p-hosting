class AuthException(Exception):
    pass


class UserAlreadyExistsError(AuthException):
    pass


class InvalidCredentialsError(AuthException):
    pass


class AccountSuspendedError(AuthException):
    pass


class InvalidTokenError(AuthException):
    pass


class UserNotFoundError(AuthException):
    pass


class InactiveUserError(AuthException):
    pass
