'Specific exceptions for SECLO driver'
class UnauthorizedAccessException(Exception):
    'Error class to raise when the server returns unauth request, meaning we should log in again'

class UnknownReportedException(Exception):
    'Error class to raise when the server returns any other type of error.'

class RecNotAccessibleException(Exception):
    '''
    Error class to raise when a case is not accessible, 
    meaning most likely it is closed and must be reopened.
    '''

class InvalidCaseStateException(Exception):
    'Error class to raise when the loaded case has an invalid state.'

class ValidationException(Exception):
    'Error class to raise when a validation has been violated in the fucking web app.'

class InvalidParameterException(Exception):
    'Error class to raise when a parameter violates expected input'

class FileDownloadTimeoutException(Exception):
    'Error class to raise when a file download attempt has timed out'

class AttemptsExceededException(Exception):
    'Error class to raise when an operation has been attempted too many times without success'
