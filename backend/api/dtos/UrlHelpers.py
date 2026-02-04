from pydantic import HttpUrl
from database.database import *

baseURL = "http://localhost:8080" #TODO Wire actual URL!

def claimToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{recID}')


def citationsToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/citation?claim={recID}')

def citationToUrl(citation: Citation) -> HttpUrl:
    return HttpUrl(baseURL + f'/citation/{citation.citationID}')


def notificationsToUrl(citationID: int):
    return HttpUrl(baseURL + f'/citation/{citationID}/notification')

def notificationToUrl(citationID: int, notificationID):
    return HttpUrl(baseURL + f'/citation/{citationID}/notification/{notificationID}')

def employeesToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{recID}/employee')

def employeeToUrl(employee: Employee) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{employee.claim.recID}/employee/{employee.employeeID}')


def employersToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{recID}/employer')

def employerToUrl(employer: Employer) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{employer.claim.recID}/employer/{employer.employerID}')


def lawyersToUrl(recID: int) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{recID}/lawyer')

def lawyerToUrl(lawyer: Lawyer) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{lawyer.claim.recID}/lawyer/{lawyer.lawyerID}')


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
