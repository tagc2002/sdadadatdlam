
#Error class to raise when the server returns unauth request, meaning we should log in again
class UnauthorizedAccessException(Exception):
    pass

#Error class to raise when the server returns any other type of error.
class UnknownReportedException(Exception):
    pass

#Error class to raise when a case is not accessible, meaning most likely it is closed and must be reopened.
class RecNotAccessibleException(Exception):
    pass

#Error class to raise when the loaded case has an invalid state.
class InvalidCaseStateException(Exception):
    pass

#Error class to raise when a validation has been violated in the fucking web app
class ValidationException(Exception):
    pass

#Error class to raise when a parameter violates expected input
class InvalidParameterException(Exception):
    pass