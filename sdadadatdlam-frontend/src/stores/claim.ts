"use strict";
import { defineStore } from 'pinia'

export const useClaimStore = defineStore('claim', () => {
    const cases = ref<Claim[]>([]);

    function getClaims(){
        return cases.value;
    }

    function getClaim(recID: number){
        cases.value.find(claim => claim.recID === recID);
    }
})

export class Claim{
    #recID: number;
    #gdeID: string;
    #initDate: string;
    #initByEmployee: boolean;
    #isDomestic: boolean;
    #claimType: number;
    #legalStuff: string;
    #calID: string;

    #citations: Citation[] = [];
    #documentation: Documentation[] = [];
    #employees: Employee[] = [];
    #employer: Employer[] = [];
    #lawyer: Lawyer[] = [];
    #agreements: Agreement[] = [];
    #nonagreements: NonAgreement[] = [];
    #complaints: Complaint[] = [];

    constructor(recID: number, gdeID: string, initDate: string, 
        initByEmployee: boolean, claimType: number, legalStuff: string,
        isDomestic: boolean, calID: string
    ){
        this.#recID = recID;
        this.#gdeID = gdeID;
        this.#initDate = initDate;
        this.#initByEmployee = initByEmployee;
        this.#claimType = claimType;
        this.#legalStuff = legalStuff;
        this.#isDomestic = isDomestic;
        this.#calID = calID;
    }

    get recID(): number{
        return this.recID;
    }
}

export class Citation{
    #citationID: number;
    #secloAudID: number;
    #citationDateTime: string;
    #citationType: number;
    #citationStatus: number;
    #citationSummary: string;
    #notes: string;
    #isCalendarPrimary: boolean;
    #meetID: string;

    #notifications: Notification[] = [];
    #lawyerToEmployee: LawyerToClientPerCitation<Employee>[] = [];
    #lawyerToEmployer: LawyerToClientPerCitation<Employer>[] = [];

    constructor(citationID: number, secloAudID: number, citationDateTime: string,
        citationType: number, citationStatus: number, citationSummary: string,
        notes: string, isCalendarPrimary: boolean, meetID: string
    ) {
        this.#citationID = citationID;
        this.#secloAudID = secloAudID;
        this.#citationDateTime = citationDateTime;
        this.#citationType = citationType;
        this.#citationStatus = citationStatus;
        this.#citationSummary = citationSummary;
        this.#notes = notes;
        this.#isCalendarPrimary = isCalendarPrimary;
        this.#meetID = meetID;
    }
}

export class Documentation{
    #docID: number;
    #docName: string;
    #docType: number;
    #fileDriveID: string;
    #importedDate: string;
    #importedFromSECLO: boolean;

    constructor(docID: number, docName: string, docType: number, fileDriveID: string,
        importedDate: string, importedFromSECLO: boolean
    ){
        this.#docID = docID;
        this.#docName = docName;
        this.#docType = docType;
        this.#fileDriveID = fileDriveID;
        this.#importedDate = importedDate;
        this.#importedFromSECLO = importedFromSECLO;
    }
}

export class Employee{
    #employeeID: number;
    #employeeName: string;
    #dni: number | null;
    #cuil: number | null;
    #isValidated: boolean;
    #birthDate: string | null;

    #addresses: InfoLink<Address>[] = [];
    #emails: InfoLink<Email>[] = [];
    #bankAccount: BankAccount | null = null;
    #notifications: Notification[] = [];

    constructor(
        employeeID: number, employeeName: string, DNI: number | null = null,
        CUIL: number | null = null, birthDate: string | null = null, 
        isValidated: boolean = false
    ) {
        this.#employeeID = employeeID;
        this.#employeeName = employeeName;
        this.#dni = DNI;
        this.#cuil = CUIL;
        this.#birthDate = birthDate;
        this.#isValidated = isValidated;
    }
}

export class Employer{
    #employerID: number;
    #employerName: string;
    #cuit: number | null;
    #personType: string;
    #requiredAs: string | null;
    #SECLORegisterDate: string | null;
    #mustRegisterSECLO: boolean;
    #isValidated: boolean;
    
    #addresses: InfoLink<Address>[] = [];
    #emails: InfoLink<Email>[] = [];
    #documentation: InfoLink<Documentation>[] = [];
    #notifications: Notification[] = [];

    #parentEmployer: Employer[] = [];
    #childEmployer: Employer[] = [];

    constructor(
        employerID: number, employerName: string, personType: string, 
        CUIT: number | null = null, requiredAs: string | null = null,
        mustRegisterSECLO: boolean = false, isValidated: boolean = false,
        SECLORegisterDate: string | null = null
    ){
        this.#employerID = employerID;
        this.#employerName = employerName;
        this.#personType = personType;
        this.#cuit = CUIT;
        this.#requiredAs = requiredAs;
        this.#mustRegisterSECLO = mustRegisterSECLO;
        this.#isValidated = isValidated;
        this.#SECLORegisterDate = SECLORegisterDate;
    }
}

export class Lawyer{
    #lawyerID: number;
    #name: string;
    #t: number;
    #f: number;
    #registeredOn: string | null;
    #registeredFrom: string | null;
    #cuit: number | null;
    #isValidated: boolean;
    #hasVAT: boolean | null;

    #bankAccount: BankAccount | null = null;
    #emails: InfoLink<Email>[] = [];
    #phones: InfoLink<Phone>[] = [];
    #documentation: InfoLink<Documentation>[] = [];

    constructor(
        lawyerID: number, name: string, T: number, F: number,
        registeredOn: string | null = null, registeredFrom: string | null = null,
        CUIT: number | null = null, isValidated: boolean = false, hasVAT: boolean | null = null
    ) {
        this.#lawyerID = lawyerID;
        this.#name = name;
        this.#t = T;
        this.#f = F;
        this.#registeredOn = registeredOn;
        this.#registeredFrom = registeredFrom;
        this.#cuit = CUIT;
        this.#isValidated = isValidated;
        this.#hasVAT = hasVAT;
    }
}

export class Notification{
    #notificationID: number;
    #notificationType: number;
    #secloPostalID: number;
    #emissionDate: string;
    #receptionDate: string;
    #deliveryCode: number;
    #deliveryDescription: string;

    #belongsTo: Employee | Employer | null = null;

    constructor(notificationID: number, notificationType: number, 
        secloPostalID: number, emissionDate: string, receptionDate: string, 
        deliveryCode: number, deliveryDescription: string 
    ){
        this.#notificationID = notificationID;
        this.#notificationType = notificationType;
        this.#secloPostalID = secloPostalID;
        this.#emissionDate = emissionDate;
        this.#receptionDate = receptionDate;
        this.#deliveryCode = deliveryCode;
        this.#deliveryDescription = deliveryDescription;
    }
}

export class BankAccount{
    #accountID: number;
    #cbu: string | null;
    #bank: string | null;
    #alias: string | null;
    #accountNumber: string | null;
    #accountType: string | null;
    #cuit: number | null;
    #isValidated: boolean;

    constructor(accountID: number, CBU: string | null = null, 
        bank: string | null = null, alias: string | null = null,
        accountNumber: string | null = null, accountType: string | null = null,
        cuit: number | null = null, isValidated: boolean = false
    ){
        this.#accountID = accountID;
        this.#cbu = CBU;
        this.#bank = bank;
        this.#alias = alias;
        this.#accountNumber = accountNumber;
        this.#accountType = accountType;
        this.#cuit = cuit;
        this.#isValidated = isValidated;
    }
}

export class Address{
    #addressID: number;
    #province: string;
    #district: string;
    #county: string;
    #street: string;
    #streetnumber: string;
    #floor: string;
    #apt: string;
    #cpa: string;
    #extra: string;
    #isVerified: boolean;

    constructor(
        addressID: number, province: string, district: string, county: string,
        street: string, streetnumber: string, floor: string, apt: string,
        cpa: string, extra: string, isVerified: boolean = false
    ){
        this.#addressID = addressID;
        this.#province = province;
        this.#district = district;
        this.#county = county;
        this.#street = street;
        this.#streetnumber = streetnumber;
        this.#floor = floor;
        this.#apt = apt;
        this.#cpa = cpa;
        this.#extra = extra;
        this.#isVerified = isVerified;
    }
}

export class Email{
    #emailID: number;
    #email: string;
    #registeredOn: string;
    #registeredFrom: string;
    #description: string;

    constructor(
        emailID: number, email: string, registeredOn: string,
        registeredFrom: string, description: string
    ){
        this.#emailID = emailID;
        this.#email = email;
        this.#registeredOn = registeredOn;
        this.#registeredFrom = registeredFrom;
        this.#description = description;
    }
}

export class Phone{
    #telID: number;
    #telephone: number;
    #prefix: number;
    #description: string;
    #obtainedFrom: string;

    constructor(
        telID: number, telephone: number, prefix: number,
        description: string, obtainedFrom: string
    ) {
        this.#telID = telID;
        this.#telephone = telephone;
        this.#prefix = prefix;
        this.#description = description;
        this.#obtainedFrom = obtainedFrom;
    }
}

export class LawyerToClientPerCitation<T>{
    #lawyer: Lawyer;
    #person: T;
    #isActualLawyer: boolean;
    #isEmpowered: boolean;
    #isSelfRepresenting: boolean;
    #clientAbsent: boolean;
    #selfAbsent: boolean;
    #description: string;

    constructor(
        lawyer: Lawyer, person: T, isEmpowered: boolean, 
        clientAbsent: boolean, selfAbsent: boolean, description: string,
        isActualLawyer: boolean = true, isSelfRepresenting: boolean = false
    ){
        this.#lawyer = lawyer;
        this.#person = person;
        this.#isActualLawyer = isActualLawyer;
        this.#isEmpowered = isEmpowered;
        this.#isSelfRepresenting = isSelfRepresenting;
        this.#clientAbsent = clientAbsent;
        this.#selfAbsent = selfAbsent;
        this.#description = description;
    }
}

export class InfoLink<T>{
    #info: T;
    #description: string;
    #isRequired: boolean;
    #SECLOUploadedOn: string;

    constructor(info: T, description: string, isRequired: boolean, SECLOUploadedOn: string){
        this.#info = info;
        this.#description = description;
        this.#isRequired = isRequired;
        this.#SECLOUploadedOn = SECLOUploadedOn;
    }
}

export class Agreement{
    #agreementID: number;
    #malignaHonorary: number;
    #malignaHonoraryExpirationRelative: number;
    #isUncashable: boolean;
    #initReason: string;
    #claimedObjects: string;
    #isDomestic: boolean;
    #hasCertificateDelivery: boolean;
    #notes: string;
    #initialSendDate: string;
    #lastSendDate: string;
    #isDraft: boolean;
    #secloNotificationDate: string;
    #signedSendDate: string;
    #lawyerHonoraryRelative: number;
    #laywerHonoraryAbsolute: number;

    #documentation: InfoLink<Documentation>[] = [];
    #extension: Employer[] = [];
    #desist: Employer[] = [];

    #hemiagreements: Hemiagreement[] = [];
    #installments: PaymentInstallment[] = [];
    #homologations: Homologation[] = [];
    #invoices: Invoice[] = [];
    #payments: Payment[] = [];
    #observations: Observation[] = [];
    #complaints: Complaint[] = [];
}  

export class NonAgreement{
    #nonID: number;
    #
}

export class Complaint{

}

export class Hemiagreement{

}

export class PaymentInstallment{

}

export class Homologation{

}

export class Invoice{

}

export class Payment{

}

export class Observation{

}