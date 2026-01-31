from pydantic import HttpUrl
from database.database import Agreement, Citation, Complaint, Documentation, Employee, Employer, Invoice, Lawyer, Nonagreement

baseURL = "https://sdadadatdlam.com" #TODO Wire actual URL!

def citationToUrl(citation: Citation) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{citation.claim.recID}/citation/{citation.citationID}')

def employeeToUrl(employee: Employee) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{employee.claim.recID}/employee/{employee.employeeID}')

def employerToUrl(employer: Employer) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{employer.claim.recID}/employer/{employer.employerID}')

def lawyerToUrl(lawyer: Lawyer) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{lawyer.claim.recID}/lawyer/{lawyer.lawyerID}')

def agreementToUrl(agreement: Agreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{agreement.claim.recID}/agreement/{agreement.agreementID}')

def nonagreementToUrl(nonagreement: Nonagreement) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{nonagreement.claim.recID}/nonagreement/{nonagreement.nonID}')

def complaintToUrl(complaint: Complaint) -> HttpUrl:
    return HttpUrl(baseURL + f'/claim/{complaint.claim.recID}/complaint/{complaint.complaintID}')

def documentationToUrl(documentation: Documentation) -> HttpUrl:
    return HttpUrl(baseURL + f'/documentation/{documentation.docID}')
