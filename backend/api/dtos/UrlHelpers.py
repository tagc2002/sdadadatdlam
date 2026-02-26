from pydantic import HttpUrl
from database.database import *

baseURL = "http://localhost:8080/api" #TODO Wire actual URL!

def claimToUrl(claim: Claim):
    return baseURL + f'/claim/{claim.recID}'

def citationsToUrl():
    return baseURL + '/citation'

def citationsClaimToUrl(claim: Claim):
    return citationsToUrl() + f'?claim={claim.recID}'

def citationToUrl(citation: Citation):
    return baseURL + f'/citation/{citation.citationID}'


def notificationsToUrl(citation: Citation):
    return citationToUrl(citation) + '/notification'

def notificationToUrl(notification: SecloNotification):
    return notificationsToUrl(notification.citation) + str(notification.notificationID)

def employeesToUrl(claim: Claim):
    return claimToUrl(claim) + '/employee'

def employeeToUrl(employee: Employee):
    return employeesToUrl(employee.claim) + f'{employee.employeeID}'


def employersToUrl(claim: Claim):
    return claimToUrl(claim) + '/employer'

def employerToUrl(employer: Employer):
    return employersToUrl(employer.claim) + f'{employer.employerID}'


def lawyersToUrl(claim: Claim):
    return claimToUrl(claim) + 'lawyer'

def lawyerToUrl(lawyer: Lawyer):
    return lawyersToUrl(lawyer.claim) + f'{lawyer.lawyerID}'


def agreementsToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/agreement?claim={recID}')

def agreementToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/agreement/{agreement.agreementID}')


def nonagreementsToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/nonagreement?claim={recID}')

def nonagreementToUrl(nonagreement: Nonagreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/nonagreement/{nonagreement.nonID}')


def complaintsToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/complaint?claim={recID}')

def complaintToUrl(complaint: Complaint) -> HttpUrl:
    return HttpUrl(baseURL + f'/complaint/{complaint.complaintID}')


def documentationToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/documentation?claim={recID}')

def documentToUrl(documentation: Documentation) -> HttpUrl:
    return HttpUrl(baseURL + f'/documentation/{documentation.docID}')


def homologationsToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/homologation?agreement={agreement.agreementID}')

def homologationToUrl(homologation: Homologation) -> HttpUrl:
    return HttpUrl(baseURL + f'/homologation/{homologation.homoID}')


def invoicesToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/invoice?agreement={agreement.agreementID}')

def invoiceToUrl(invoice: Invoice) -> HttpUrl:
    return HttpUrl(baseURL + f'/invoice/{invoice.invoiceID}')


def paymentsToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/payment?agreement={agreement.agreementID}')

def paymentToUrl(payment: Payment) -> HttpUrl:
    return HttpUrl(baseURL + f'/payment/{payment.paymentID}')


def observationsToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/observation?agreement={agreement.agreementID}')

def observationToUrl(observation: Observation) -> HttpUrl:
    return HttpUrl(baseURL + f'/observation/{observation.obsID}')

def employeeBankAccountToUrl(bankAccount: BankAccount) -> HttpUrl:
    if not bankAccount.employee: raise ValueError(f"bank account {bankAccount.accountID} missing employee")
    return HttpUrl(baseURL + f'/claim/{bankAccount.employee.recID}/employee/{bankAccount.employee.employeeID}/bankAccount')

def employeeEmailsUrl(employee: Employee) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{employee.recID}/employee/')