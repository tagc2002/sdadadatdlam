CREATE TABLE claim(
    recID INT NOT NULL,
    gdeID VARCHAR(30) NOT NULL,
    creationDate TIMESTAMP NOT NULL,
    initByEmployee BOOLEAN,
    claimType TEXT,
    legalStuff TEXT,
    isDomestic BOOLEAN,
    calID TEXT,
    PRIMARY KEY(recID),
    UNIQUE(gdeID)
);
CREATE TABLE citation(
    citationID SERIAL,
    recID INT,
    secloAudID INT,
    citationDate TIMESTAMP,
    citationType TEXT,
    citationStatus INT,
    sumamry TEXT,
    PRIMARY KEY(citationID),
    FOREIGN KEY(recID) REFERENCES claim,
    UNIQUE(secloAudID)
);
CREATE TABLE documentation(
    docID SERIAL,
    docName TEXT,
    docType TEXT,
    fileDriveID TEXT,
    requestedDate TIMESTAMP,
    importedDate TIMESTAMP,
    importedFromSECLO BOOLEAN,
    uploadedDate TIMESTAMP,
    PRIMARY KEY(docID),
);
CREATE TABLE address(
    addressID SERIAL,
    province TEXT,
    district TEXT,
    county TEXT,
    street TEXT,
    streetnumber TEXT,
    floor TEXT,
    apt TEXT,
    CPA TEXT,
    PRIMARY KEY(addressID)
);
CREATE TABLE email(
    emailID SERIAL,
    email TEXT,
    registeredOn TIMESTAMP,
    registeredFrom TEXT,
    description TEXT,
    PRIMARY KEY(emailID)
);
CREATE TABLE employee(
    employeeID SERIAL,
    recID INT NOT NULL,
    employeeName TEXT NOT NULL,
    DNI INT,
    CUIL INT,
    validated BOOLEAN,
    birthDate TIMESTAMP,
    CBU TEXT,
    bank TEXT,
    alias TEXT,
    accountNumber TEXT,
    PRIMARY KEY(employeeID),
    FOREIGN KEY(recID) REFERENCES claim
);
CREATE TABLE employeeAddressLink(
    employeeID INT,
    addressID INT,
    description TEXT,
    PRIMARY KEY(employeeID, addressID),
    FOREIGN KEY(employeeID) REFERENCES employee,
    FOREIGN KEY(addressID) REFERENCES address
);
CREATE TABLE employeeEmailLink(
    emailID INT,
    employeeID INT,
    PRIMARY KEY(emailID, employeeID),
    FOREIGN KEY(employeeID) REFERENCES employee,
    FOREIGN KEY(emailID) REFERENCES email
);
CREATE TABLE employer(
    employerID SERIAL,
    recID INT NOT NULL,
    employerName TEXT NOT NULL,
    CUIT INT,
    personType INT,
    requiredAs INT,
    secloRegisterDate TIMESTAMP,
    mustRegisterSECLO BOOLEAN,
    validated BOOLEAN,
    PRIMARY KEY(employerID),
    FOREIGN KEY(recID) REFERENCES claim,
);
CREATE TABLE employerAddressLink(
    employerID INT,
    addressID INT,
    description TEXT,
    PRIMARY KEY(employerID, addressID),
    FOREIGN KEY(employerID) REFERENCES employer,
    FOREIGN KEY(addressID) REFERENCES address
);
CREATE TABLE employerEmailLink(
    emailID INT,
    employerID INT,
    PRIMARY KEY(emailID, employerID),
    FOREIGN KEY(employerID) REFERENCES employer,
    FOREIGN KEY(emailID) REFERENCES email
);
CREATE TABLE lawyer(
    lawyerID SERIAL,
    recID INT,
    laywerName TEXT,
    lawyerTF INT,
    registeredOn TIMESTAMP,
    registeredFrom TEXT,
    CBU TEXT,
    bank TEXT,
    alias TEXT,
    accountNumber TEXT,
    CUIT INT,
    hasVAT BOOLEAN,
    PRIMARY KEY(lawyerID),
    FOREIGN KEY(recID) REFERENCES claim
);
CREATE TABLE lawyerEmailLink(
    emailID INT,
    lawyerID INT,
    PRIMARY KEY(emailID, lawyerID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer,
    FOREIGN KEY(emailID) REFERENCES email
);
CREATE TABLE lawyerToEmployee(
    lawyerID INT,
    employeeID INT,
    citationID INT,
    isActualLawyer BOOLEAN,
    PRIMARY KEY(lawyerID, employeeID, citationID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer,
    FOREIGN KEY(employeeID) REFERENCES employee,
    FOREIGN KEY(citationID) REFERENCES citation
);
CREATE TABLE lawyerToEmployer(
    lawyerID INT,
    employerID INT,
    citationID INT,
    isActualLawyer BOOLEAN,
    isEmpowered BOOLEAN,
    isSelfRepresenting BOOLEAN,
    PRIMARY KEY(lawyerID, employerID, citationID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer,
    FOREIGN KEY(employerID) REFERENCES employer,
    FOREIGN KEY(citationID) REFERENCES citation
);
CREATE TABLE employerRelation(
    masterID INT,
    slaveID INT,
    relationship INT,
    PRIMARY KEY(masterID, slaveID),
    FOREIGN KEY(masterID) REFERENCES employer,
    FOREIGN KEY(slaveID) REFERENCES employer,
);
CREATE TABLE documentationEmployeeLink(
    docID INT,
    employeeID INT,
    description TEXT,
    isRequired BOOLEAN,
    PRIMARY KEY(docID, employeeID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(employeeID) REFERENCES employee
);
CREATE TABLE documentationEmployerLink(
    docID INT,
    employerID INT,
    description TEXT,
    isRequired BOOLEAN,
    PRIMARY KEY(docID, employerID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(employerID) REFERENCES employer
);
CREATE TABLE documentationLawyerLink(
    docID INT,
    lawyerID INT,
    description TEXT,
    isRequired BOOLEAN,
    PRIMARY KEY(docID, lawyerID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(lawyerID) REFERENCES lawyer
);
CREATE TABLE lawyerTelephone(
    lawyerID INT,
    telephone INT,
    telephonePrefix INT,
    description TEXT,
    PRIMARY KEY(lawyerID, telephone),
    FOREIGN KEY(lawyerID) REFERENCES lawyer
);
CREATE TABLE notification(
    notificationID SERIAL,
    citationID INT,
    employeeID INT,
    employerID INT,
    notificationType INT,
    secloPostalID INT,
    emissionDate TIMESTAMP,
    receptionDate TIMESTAMP,
    deliveryCode INT,
    deliveryDescription TEXT,
    isAbsent BOOLEAN,
    PRIMARY KEY(notificationID),
    FOREIGN KEY(citationID) REFERENCES citation,
    FOREIGN KEY(employeeID) REFERENCES employee,
    FOREIGN KEY(employerID) REFERENCES employer,
);
CREATE TABLE agreement(
    agreementID SERIAL,
    recID INT NOT NULL,
    citationID INT NOT NULL,
    invoiceTo INT,
    malignaHonorary DECIMAL(20,2),
    expirationRelative INTERVAL,
    presentationDate TIMESTAMP,
    isUncashable BOOLEAN,
    initReason TEXT,
    claimedObjects TEXT,
    hasCertificateDelivery BOOLEAN,
    notes TEXT,
    sentDate TIMESTAMP,
    isDraft BOOLEAN
    PRIMARY KEY(agreementID),
    FOREIGN KEY(recID) REFERENCES claim,
    FOREIGN KEY(invoiceTo) REFERENCES employer,
    FOREIGN KEY(citationID) REFERENCES citation
);
CREATE TABLE agreementExtension(
    agreementID INT,
    employerID INT,
    PRIMARY KEY(agreementID, employerID),
    FOREIGN KEY(agreementID) REFERENCES agreement,
    FOREIGN KEY(employerID) REFERENCES employer
);
CREATE TABLE agreementDesist(
    agreementID INT,
    employerID INT,
    PRIMARY KEY(agreementID, employerID),
    FOREIGN KEY(agreementID) REFERENCES agreement,
    FOREIGN KEY(employerID) REFERENCES employer
);
CREATE TABLE documentationAgreementLink(
    docID INT,
    agreementID INT,
    description TEXT,
    isRequired BOOLEAN,
    PRIMARY KEY(docID, agreementID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(agreementID) REFERENCES agreement
);
CREATE TABLE hemiagreement(
    hemiID SERIAL,
    agreementID INT NOT NULL,
    amountARS DECIMAL(20,2) NOT NULL,
    amountUSD DECIMAL(20,2),
    employeeID INT NOT NULL,
    honoraryRelative DECIMAL(3,2),
    honoraryAbsolute DECIMAL(20,2),
    PRIMARY KEY(hemiID),
    FOREIGN KEY(agreementID) REFERENCES agreement,
    FOREIGN KEY(employeeID) REFERENCES employee
);
CREATE TABLE paymentInstallment(
    installmentID SERIAL,
    hemiID INT,
    amount DECIMAL(20,2) NOT NULL,
    expirationHomo INTERVAL,
    expirationRelative INTERVAL,
    expirationAbsolute TIMESTAMP,
    wasPaidBefore BOOLEAN,
    customPaymentMethod TEXT,
    PRIMARY KEY(installmentID),
    FOREIGN KEY(hemiID) references hemiagreement
);
CREATE TABLE homologation(
    homoID SERIAL,
    gdeID INT,
    agreementID INT,
    signDate TIMESTAMP,
    draftDate TIMESTAMP,
    notificationDate TIMESTAMP,
    description TEXT,
    PRIMARY KEY(homoID),
    FOREIGN KEY(agreementID) REFERENCES agreement,
);
CREATE TABLE documentationHomologationLink(
    docID INT,
    homoID INT,
    description TEXT,
    PRIMARY KEY(docID, homoID),
    FOREIGN KEY(homoID) REFERENCES homologation,
    FOREIGN KEY(docID) REFERENCES documentation
);
CREATE TABLE invoice(
    invoiceID SERIAL,
    agreementID INT,
    afipID TEXT,
    emissionDate TIMESTAMP,
    CUIT INT,
    amount DECIMAL(20,2),
    description TEXT,
    isCredit BOOLEAN,
    PRIMARY KEY(invoiceID),
    FOREIGN KEY(agreementID) REFERENCES agreement,
    UNIQUE(afipID)
);
CREATE TABLE documentationInvoiceLink(
    invoiceID INT,
    docID INT,
    PRIMARY KEY(invoiceID, docID),
    FOREIGN KEY(invoiceID) REFERENCES invoice,
    FOREIGN KEY(docID) REFERENCES documentation
);
CREATE TABLE payment(
    paymentID SERIAL,
    agreementID INT,
    amount DECIMAL(20,2),
    paymentDate TIMESTAMP,
    notifiedDate TIMESTAMP,
    bankReference TEXT,
    description TEXT,
    isEvilified BOOLEAN,
	PRIMARY KEY(paymentID),
	FOREIGN KEY(agreementID) REFERENCES agreement
);
CREATE TABLE documentationPaymentLink(
    docID INT,
    paymentID INT,
    PRIMARY KEY(docID, paymentID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(paymentID) REFERENCES payment
);
CREATE TABLE observation(
    obsID SERIAL, 
    agreementID INT,
    obsDate TIMESTAMP,
    reason TEXT,
    description TEXT,
    notifiedDate TIMESTAMP,
    replyDate TIMESTAMP,
    secloEmailNotificationDate TIMESTAMP,
    PRIMARY KEY(paymentID),
    FOREIGN KEY(agreementID) REFERENCES agreement
);
CREATE TABLE documentationObservationLink(
    docID INT,
    obsID INT,
    PRIMARY KEY(docID, obsID),
    FOREIGN KEY(docID) REFERENCES documentation,
    FOREIGN KEY(obsID) REFERENCES observation
);
CREATE TABLE complaint(
    compID SERIAL,
    recID INT,
    description TEXT,
    complainDate TIMESTAMP,
    recipient TEXT,
    reason TEXT,
    channel TEXT,
    ackDate TIMESTAMP,
    reply TEXT,
    PRIMARY KEY(compID),
    FOREIGN KEY(recID) REFERENCES claim
);
CREATE TABLE complaintAgreementLink(
    compID INT,
    agreementID INT,
    PRIMARY KEY(compID, agreementID),
    FOREIGN KEY(compID) REFERENCES complaint,
    FOREIGN KEY(agreementID) REFERENCES agreement
);
CREATE TABLE complaintHomologationLink(
    compID INT,
    homoID INT,
    PRIMARY KEY(compID, homoID),
    FOREIGN KEY(compID) REFERENCES complaint,
    FOREIGN KEY(homoID) REFERENCES homologation
);
CREATE TABLE complaintPaymentLink(
    compID INT,
    paymentID INT,
    PRIMARY KEY(compID, paymentID),
    FOREIGN KEY(compID) REFERENCES complaint,
    FOREIGN KEY(paymentID) REFERENCES payment
);
CREATE TABLE complaintObservationLink(
    compID INT,
    obsID INT,
    PRIMARY KEY(compID, obsID),
    FOREIGN KEY(compID) REFERENCES complaint,
    FOREIGN KEY(obsID) REFERENCES observation
);
CREATE TABLE nonagreement(
    nonID SERIAL,
    recID INT,
    citationID INT,
    claims TEXT,
    bonusData TEXT,
    presentationDate TEXT,
    sentDate TEXT,
    notes TEXT,
    PRIMARY KEY(nonID),
    FOREIGN KEY(recID) REFERENCES claim,
    FOREIGN KEY(citationID) REFERENCES citation
);
CREATE TABLE nonagreementInvoice(
    secloInvoiceID INT,
    total DECIMAL(20,2),
    date TIMESTAMP,
    paymentDate TIMESTAMP,
    PRIMARY KEY(secloInvoiceID)
);
CREATE TABLE nonagreementInvoiceLink(
    secloInvoiceID INT, 
    nonID INT,
    amount DECIMAL(20,2),
    dateRegistered TIMESTAMP,
    PRIMARY KEY(secloInvoiceID, nonID),
    FOREIGN KEY(secloInvoiceID) REFERENCES nonagreementInvoice,
    FOREIGN KEY(nonID) REFERENCES nonagreement
);
CREATE TABLE monthlyHonorary(
    amount DECIMAL(20,2),
    validSince TIMESTAMP,
    PRIMARY KEY(validSince)
);
CREATE TABLE bratInvoice(
    bratID SERIAL,
    expenses DECIMAL(20,2),
    bonusPercentual DECIMAL(20,2),
    deductions DECIMAL(20,2),
    bonusRaw DECIMAL(20,2),
    percentage DECIMAL(3,2),
    description TEXT,
    PRIMARY KEY(bratID)
);
CREATE TABLE bratAgreements(
    bratID INT,
    agreementID INT,
    PRIMARY KEY(bratID, agreementID),
    FOREIGN KEY(bratID) REFERENCES bratInvoice,
    FOREIGN KEY(agreementID) REFERENCES agreement
);
CREATE TABLE bratNonAgreements(
    bratID INT,
    SECLOInvoiceID INT,
    PRIMARY KEY(bratID, SECLOInvoiceID),
    FOREIGN KEY(bratID) REFERENCES bratInvoice,
    FOREIGN KEY(SECLOInvoiceID) REFERENCES nonagreementInvoice
);