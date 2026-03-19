from datetime import datetime
from pathlib import Path
from typing import Self
from attr import dataclass
from pypdf import PdfReader
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from database.database import Agreement, Homologation
from dataobjects.enums import DocType
from domainlogic.documentationmanager import DocumentationManager
from repositories.SECLO.SECLODriver import SECLOFileManager, SECLOLoginCredentials
from repositories.SECLO.SECLOProgressReporting import ProgressReport

@dataclass
class HomologationInfo:
    isApproved: bool
    gdeID: str | None
    signedDate: datetime | None

class HomologationManager():
    @staticmethod
    def parseHomoPDFData(pdf: Path) -> HomologationInfo:
        reader = PdfReader(pdf)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        isApproved="Homologar el acuerdo conciliatorio" in text

        fields = reader.get_fields()
        if fields and 'signature_0' in fields:
            date = datetime.strptime(fields['signature_0'].value['/M'][2:19]+"00", "%Y%m%d%H%M%S%z")
            return HomologationInfo(isApproved=isApproved,
                                    gdeID=fields["numero_documento"].value,
                                    signedDate=date)
        return HomologationInfo(isApproved=isApproved, gdeID=None, signedDate=None)
    
    @staticmethod
    def saveHomologation(path: Path, info: HomologationInfo, agreement: Agreement, db: Session) -> Homologation:
        document = DocumentationManager().storeFile(name="Homologacion", type=DocType.HOMOLOGATION if info.gdeID else DocType.HOMOLOGATION_DRAFT, isSeclo=True, path=path, db=db)
        homo = Homologation(gdeID=info.gdeID, agreement=agreement, 
                            signedDate=info.signedDate, isApproved=info.isApproved, 
                            registeredDate=datetime.now(), document=document)
        db.add(homo)
        return homo    

    def checkHomologation(self: Self, agreement: Agreement, db: Session, creds: SECLOLoginCredentials):
        with SECLOFileManager(credentials=creds, recid=agreement.recID) as seclo:
            files = seclo.setRecId(agreement.recID).getFiles()
            for fileIndex, fileEntry in enumerate(files):
                if "Disposici" in fileEntry[0]: #regular homologation
                    file = seclo.getFile(fileIndex)
                    homoInfo = self.parseHomoPDFData(file)
                    if homoInfo.gdeID:    #is valid (aka not a draft)
                        for homologation in agreement.homologations:
                            if homologation.gdeID == homoInfo.gdeID:    #already stored, bummer
                                break
                        else: #brand new homologation
                            for homologation in agreement.homologations: #delete any drafts
                                if not homologation.signedDate:
                                    if homologation.document: db.delete(homologation.document)
                                    db.delete(homologation)
                            self.saveHomologation(file, homoInfo, agreement, db)
                    else:   #is draft
                        for homologation in agreement.homologations:
                            if not homologation.signedDate and homologation.registeredDate >= fileEntry[2]: #already registered draft
                                break
                        else:
                            self.saveHomologation(file, homoInfo, agreement, db)
                elif "Documento con firma digital" in fileEntry[0] and agreement.signedSendDate and fileEntry[2] > agreement.signedSendDate:
                    file = seclo.getFile(fileIndex)
                    homoInfo = self.parseHomoPDFData(file)
                    if homoInfo.gdeID:  #is valid
                        savedHomo = self.saveHomologation(file, homoInfo, agreement, db)
                        if savedHomo: return savedHomo
                    #theres no such thing as a domestic homologation draft
        
    def batchCheckHomologations(self: Self, db: Session, creds: SECLOLoginCredentials, progress: ProgressReport) -> None:
        missing = db.scalars(select(Agreement).distinct(Agreement.agreementID).join(Homologation, isouter=True)\
                             .where(Agreement.signedSendDate != None)\
                             .where(or_(Homologation.signedDate == None, ~Agreement.homologations.any(), \
                                        and_(Homologation.isApproved==False, Homologation.complaintLink.any())
                            ))).all()
        progress.setSteps(len(missing))
        found = 0

        for index, agreement in enumerate(missing):
            progress.increaseProgress(1, f"Getting documentation ({index+1} of {len(missing)}) {"{found} found" if found > 0 else ""}")
            self.checkHomologation(agreement, db, creds)