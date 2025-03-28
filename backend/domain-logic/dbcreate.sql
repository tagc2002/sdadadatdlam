CREATE TABLE claim(
    recID INT NOT NULL PRIMARY KEY,
    gdeID VARCHAR(30) NOT NULL UNIQUE,
    creationDate TIMESTAMP NOT NULL,
    initByEmployee BOOLEAN,
    claimType TEXT,
    legalStuff TEXT,
    isDomestic BOOLEAN,
    calID TEXT
);
CREATE TABLE citation(
    citationID SERIAL PRIMARY KEY,
    recID INT,
    secloAudID INT UNIQUE NOT NULL,
    citationDate TIMESTAMP,
    citationType TEXT NOT NULL,
    citationStatus INT,
    citationSummary TEXT,
    notes TEXT,
    isCalendarPrimary BOOLEAN NOT NULL,
    meetID TEXT,
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentation(
    docID SERIAL PRIMARY KEY,
    docName TEXT NOT NULL,
    docType TEXT,
    fileDriveID TEXT,
    importedDate TIMESTAMP,
    importedFromSECLO BOOLEAN
);
CREATE TABLE bankAccount(
    accountID SERIAL PRIMARY KEY,
    CBU1 INT NOT NULL,
    CBU2 INT NOT NULL,
    bankName TEXT NOT NULL,
    alias TEXT,
    accountNumber BIGINT,
    CUIT BIGINT,
    isValidated BOOLEAN
);
CREATE TABLE address(
    addressID SERIAL PRIMARY KEY,
    province TEXT,
    district TEXT,
    county TEXT,
    street TEXT,
    streetnumber TEXT,
    floor TEXT,
    apt TEXT,
    CPA TEXT,
    extra TEXT
);
CREATE TABLE email(
    emailID SERIAL PRIMARY KEY,
    email TEXT,
    registeredOn TIMESTAMP,
    registeredFrom TEXT,
    description TEXT
);
CREATE TABLE employee(
    employeeID SERIAL,
    recID INT NOT NULL,
    employeeName TEXT NOT NULL,
    DNI INT NOT NULL,
    CUIL INT,
    isValidated BOOLEAN NOT NULL,
    birthDate TIMESTAMP,
    bankAccount INT,
    PRIMARY KEY(employeeID),
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(bankAccount) REFERENCES bankAccount ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE TABLE employeeAddressLink(
    employeeID INT,
    addressID INT,
    description TEXT,
    PRIMARY KEY(employeeID, addressID),
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(addressID) REFERENCES address ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE employeeEmailLink(
    emailID INT,
    employeeID INT,
    PRIMARY KEY(emailID, employeeID),
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(emailID) REFERENCES email ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE employer(
    employerID SERIAL,
    recID INT NOT NULL,
    employerName TEXT NOT NULL,
    CUIT INT,
    personType INT NOT NULL,
    requiredAs INT,
    secloRegisterDate TIMESTAMP,
    mustRegisterSECLO BOOLEAN,
    isValidated BOOLEAN NOT NULL,
    isDesisted BOOLEAN NOT NULL, 
    PRIMARY KEY(employerID),
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE employerAddressLink(
    employerID INT,
    addressID INT,
    description TEXT,
    PRIMARY KEY(employerID, addressID),
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(addressID) REFERENCES address ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE employerEmailLink(
    emailID INT,
    employerID INT,
    PRIMARY KEY(emailID, employerID),
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(emailID) REFERENCES email ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawyer(
    lawyerID SERIAL,
    recID INT,
    laywerName TEXT,
    T INT NOT NULL,
    F INT NOT NULL,
    registeredOn TIMESTAMP,
    registeredFrom TEXT,
    CUIT BIGINT,
    hasVAT BOOLEAN,
    isValidated BOOLEAN NOT NULL,
    bankAccount INT,
    PRIMARY KEY(lawyerID),
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(bankAccount) REFERENCES bankAccount ON DELETE SET NULL ON UPDATE CASCADE
); 
CREATE TABLE lawyerToEmployee(
    lawyerID INT NOT NULL,
    employeeID INT NOT NULL,
    citationID INT NOT NULL,
    isActualLawyer BOOLEAN,
    clientAbsent BOOLEAN NOT NULL,
    description TEXT,
    PRIMARY KEY(lawyerID, employeeID, citationID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE, 
    FOREIGN KEY(citationID) REFERENCES citation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawyerToEmployer(
    lawyerID INT NOT NULL,
    employerID INT NOT NULL,
    citationID INT NOT NULL,
    isActualLawyer BOOLEAN NOT NULL,
    isEmpowered BOOLEAN NOT NULL,
    isSelfRepresenting BOOLEAN NOT NULL,
    clientAbsent BOOLEAN NOT NULL,
    PRIMARY KEY(lawyerID, employerID, citationID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer,
    FOREIGN KEY(employerID) REFERENCES employer,
    FOREIGN KEY(citationID) REFERENCES citation
);
CREATE TABLE lawyerEmailLink(
    emailID INT NOT NULL,
    lawyerID INT NOT NULL,
    PRIMARY KEY(emailID, lawyerID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(emailID) REFERENCES email ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE employerRelation(
    masterID INT NOT NULL,
    slaveID INT NOT NULL,
    relationship TEXT,
    PRIMARY KEY(masterID, slaveID),
    FOREIGN KEY(masterID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(slaveID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentationEmployeeLink(
    docID INT NOT NULL,
    employeeID INT NOT NULL,
    description TEXT,
    isRequired BOOLEAN,
    SECLOUploadedOn TIMESTAMP,
    PRIMARY KEY(docID, employeeID),
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentationEmployerLink(
    docID INT,
    employerID INT,
    description TEXT,
    isRequired BOOLEAN,
    SECLOUploadedOn TIMESTAMP,
    PRIMARY KEY(docID, employerID),
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentationLawyerLink(
    docID INT,
    lawyerID INT,
    description TEXT,
    isRequired BOOLEAN,
    SECLOUploadedOn TIMESTAMP,
    PRIMARY KEY(docID, lawyerID),
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(lawyerID) REFERENCES lawyer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE telephone(
    telID SERIAL PRIMARY KEY,
    telephone INT NOT NULL,
    prefix INT NOT NULL,
    description TEXT
);
CREATE TABLE lawyerTelephoneLink(
    lawyerID INT NOT NULL,
    telID INT NOT NULL,
    description TEXT,
    PRIMARY KEY(lawyerID, telID),
    FOREIGN KEY(lawyerID) REFERENCES lawyer ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(telID) REFERENCES telephone ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE secloNotification(
    notificationID SERIAL,
    citationID INT NOT NULL,
    notificationType INT NOT NULL,
    secloPostalID INT,
    emissionDate TIMESTAMP NOT NULL, 
    receptionDate TIMESTAMP,
    deliveryCode INT,
    deliveryDescription TEXT,
    PRIMARY KEY(notificationID),
    FOREIGN KEY(citationID) REFERENCES citation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE secloNotificationToEmployee(
    notificationID INT NOT NULL,
    employeeID INT NOT NULL,
    PRIMARY KEY(notificationID, employeeID),
    FOREIGN KEY(notificationID) REFERENCES secloNotification ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE secloNotificationToEmployer(
    notificationID INT NOT NULL,
    employerID INT NOT NULL,
    PRIMARY KEY(notificationID, employerID),
    FOREIGN KEY(notificationID) REFERENCES secloNotification ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE agreement(
    agreementID SERIAL,
    recID INT NOT NULL,
    citationID INT NOT NULL,
    invoiceTo INT,
    malignaHonorary DECIMAL(20,2) NOT NULL,
    expirationRelative INTERVAL,
    presentationDate TIMESTAMP,
    isUncashable BOOLEAN,
    initReason TEXT,
    claimedObjects TEXT,
    hasCertificateDelivery BOOLEAN,
    notes TEXT,
    initialSentDate TIMESTAMP,
    lastSentDate TIMESTAMP,
    isDraft BOOLEAN,
    PRIMARY KEY(agreementID),
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(invoiceTo) REFERENCES employer ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY(citationID) REFERENCES citation ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE TABLE agreementExtension(
    agreementID INT,
    employerID INT,
    PRIMARY KEY(agreementID, employerID),
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE agreementDesist(
    agreementID INT,
    employerID INT,
    PRIMARY KEY(agreementID, employerID),
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employerID) REFERENCES employer ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentationAgreementLink(
    docID INT,
    agreementID INT,
    description TEXT,
    isRequired BOOLEAN,
    PRIMARY KEY(docID, agreementID),
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE
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
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(employeeID) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE paymentInstallment(
    installmentID SERIAL,
    hemiID INT NOT NULL,
    amount DECIMAL(20,2) NOT NULL,
    expirationHomo INTERVAL,
    expirationRelative INTERVAL,
    expirationAbsolute TIMESTAMP,
    wasPaidBefore BOOLEAN,
    customPaymentMethod TEXT,
    PRIMARY KEY(installmentID),
    FOREIGN KEY(hemiID) references hemiagreement ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE homologation(
    homoID SERIAL,
    gdeID TEXT,
    agreementID INT,
    signDate TIMESTAMP,
    registeredDate TIMESTAMP,
    notificationDate TIMESTAMP,
    description TEXT,
    docID INT,
    PRIMARY KEY(homoID),
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE
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
    relatedTo INT,
    PRIMARY KEY(invoiceID),
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(relatedTo) REFERENCES invoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE payment(
    paymentID SERIAL,
    agreementID INT,
    amount DECIMAL(20,2),
    paymentDate TIMESTAMP,
    notifiedDate TIMESTAMP,
    notifiedBy TEXT,
    bankReference TEXT,
    description TEXT,
    isEvilified BOOLEAN,
    docID INT,
	PRIMARY KEY(paymentID),
	FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE observation(
    obsID SERIAL, 
    agreementID INT NOT NULL,
    obsDate TIMESTAMP NOT NULL,
    reason TEXT NOT NULL,
    description TEXT,
    notifiedDate TIMESTAMP,
    replyDate TIMESTAMP,
    secloEmailNotificationDate TIMESTAMP,
    PRIMARY KEY(obsID),
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE documentationObservationLink(
    docID INT,
    obsID INT,
    PRIMARY KEY(docID, obsID),
    FOREIGN KEY(docID) REFERENCES documentation ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(obsID) REFERENCES observation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE complaint(
    complaintID SERIAL,
    recID INT,
    description TEXT,
    complainDate TIMESTAMP,
    recipient TEXT,
    reason TEXT,
    channel TEXT,
    ackDate TIMESTAMP,
    reply TEXT,
    PRIMARY KEY(complaintID),
    FOREIGN KEY(recID) REFERENCES claim ON UPDATE CASCADE ON DELETE CASCADE
);
CREATE TABLE complaintAgreementLink(
    complaintID INT,
    agreementID INT,
    PRIMARY KEY(complaintID, agreementID),
    FOREIGN KEY(complaintID) REFERENCES complaint ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE complaintHomologationLink(
    complaintID INT,
    homoID INT,
    PRIMARY KEY(complaintID, homoID),
    FOREIGN KEY(complaintID) REFERENCES complaint ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(homoID) REFERENCES homologation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE complaintPaymentLink(
    complaintID INT,
    paymentID INT,
    PRIMARY KEY(complaintID, paymentID),
    FOREIGN KEY(complaintID) REFERENCES complaint ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(paymentID) REFERENCES payment ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE complaintObservationLink(
    complaintID INT,
    obsID INT,
    PRIMARY KEY(complaintID, obsID),
    FOREIGN KEY(complaintID) REFERENCES complaint ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(obsID) REFERENCES observation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE nonagreement(
    nonID SERIAL,
    recID INT NOT NULL,
    citationID INT NOT NULL,
    claims TEXT NOT NULL,
    bonusData TEXT,
    sentDate TEXT,
    notes TEXT,
    waitToSend BOOLEAN NOT NULL,
    PRIMARY KEY(nonID),
    FOREIGN KEY(recID) REFERENCES claim ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(citationID) REFERENCES citation ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE nonagreementSECLOInvoice(
    secloInvoiceID INT,
    amoutn DECIMAL(20,2),
    periodDate TIMESTAMP,
    paymentDate TIMESTAMP,
    PRIMARY KEY(secloInvoiceID)
);
CREATE TABLE nonagreementInvoiceLink(
    secloInvoiceID INT, 
    nonID INT,
    reopening BOOLEAN,
    amount DECIMAL(20,2),
    dateRegistered TIMESTAMP,
    PRIMARY KEY(secloInvoiceID, nonID, reopening, dateRegistered),
    FOREIGN KEY(secloInvoiceID) REFERENCES nonagreementSECLOInvoice ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(nonID) REFERENCES nonagreement ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratInvoice(
    bratID SERIAL,
    percentage DECIMAL(3,2),
    description TEXT,
    PRIMARY KEY(bratID)
);
CREATE TABLE bratAgreements(
    bratID INT,
    agreementID INT,
    PRIMARY KEY(bratID, agreementID),
    FOREIGN KEY(bratID) REFERENCES bratInvoice ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(agreementID) REFERENCES agreement ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratNonAgreements(
    bratID INT,
    SECLOInvoiceID INT,
    PRIMARY KEY(bratID, SECLOInvoiceID),
    FOREIGN KEY(bratID) REFERENCES bratInvoice ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(SECLOInvoiceID) REFERENCES nonagreementSECLOInvoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratBonusPercentual(
    bratID INT, 
    amount DECIMAL(20,2),
    description TEXT,
    PRIMARY KEY(bratID, amount, description),
    FOREIGN KEY(bratID) references bratInvoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratDeductionPercentual(
    bratID INT, 
    amount DECIMAL(20,2),
    description TEXT,
    PRIMARY KEY(bratID, amount, description),
    FOREIGN KEY(bratID) references bratInvoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratBonusAbsolute(
    bratID INT, 
    amount DECIMAL(20,2),
    description TEXT,
    PRIMARY KEY(bratID, amount, description),
    FOREIGN KEY(bratID) references bratInvoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE bratDeductionAbsolute(
    bratID INT, 
    amount DECIMAL(20,2),
    description TEXT,
    PRIMARY KEY(bratID, amount, description),
    FOREIGN KEY(bratID) references bratInvoice ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE monthlyHonorary(
    id SERIAL,
    amount DECIMAL(20,2) NOT NULL,
    validSince TIMESTAMP NOT NULL,
    importedOn TIMESTAMP NOT NULL,
    signedDisposition BOOLEAN NOT NULL,
    PRIMARY KEY(id)
);
CREATE TABLE lawyerDirectory(
    lawyerID SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    T INT NOT NULL,
    F INT NOT NULL,
    CUIT INT,
    bankAccount INT,
    FOREIGN KEY(bankAccount) REFERENCES bankAccount ON UPDATE CASCADE ON DELETE SET NULL
);
CREATE TABLE companyDirectory(
    CUIT INT PRIMARY KEY,
    name TEXT NOT NULL
)
CREATE TABLE lawyerCompanyDirectoryLink(
    CUIT INT,
    lawyerID INT,
    autoNotify BOOLEAN,
    PRIMARY KEY(CUIT, lawyerID),
    FOREIGN KEY(CUIT) REFERENCES companyDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(lawyerID) REFERENCES lawyerDirectory ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawfirmDirectory(
    lawfirmID SERIAL PRIMARY KEY,
    lawfirmName TEXT
);
CREATE TABLE lawfirmLawyerLink(
    lawfirmID INT NOT NULL,
    lawyerID INT NOT NULL,
    PRIMARY KEY(lawfirmID, lawyerID),
    FOREIGN KEY(lawfirmID) REFERENCES lawfirmDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(lawyerID) REFERENCES lawyerDirectory ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawfirmCompanyDirectoryLink(
    lawfirmID INT NOT NULL,
    companyID INT NOT NULL,
    autoNotify BOOLEAN,
    PRIMARY KEY(lawfirmID, companyID),
    FOREIGN KEY(lawfirmID) REFERENCES lawfirmDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(companyID) REFERENCES companyDirectory ON DELETE CASCADE ON UPDATE CASCADE   
);
CREATE TABLE lawyerDirectoryTelephoneLink(
    lawyerID INT NOT NULL,
    telID INT NOT NULL,
    description TEXT,
    PRIMARY KEY(lawyerID, telID),
    FOREIGN KEY(lawyerID) REFERENCES lawyerDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(telID) REFERENCES telephone ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawfirmDirectoryTelephoneLink(
    lawfirmID INT NOT NULL,
    telID INT NOT NULL,
    description TEXT,
    PRIMARY KEY(lawfirmID, telID),
    FOREIGN KEY(lawfirmID) REFERENCES lawfirmDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(telID) REFERENCES telephone ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawyerDirectoryEmailLink(
    lawyerID INT NOT NULL,
    emailID INT NOT NULL,
    description TEXT,
    PRIMARY KEY(lawyerID, emailID),
    FOREIGN KEY(lawyerID) REFERENCES lawyerDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(emailID) REFERENCES email ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE lawfirmDirectoryEmailLink(
    lawfirmID INT NOT NULL,
    emailID INT NOT NULL,
    description TEXT,
    PRIMARY KEY(lawfirmID, emailID),
    FOREIGN KEY(lawfirmID) REFERENCES lawfirmDirectory ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(emailID) REFERENCES email ON DELETE CASCADE ON UPDATE CASCADE
);