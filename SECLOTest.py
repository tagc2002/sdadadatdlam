from datetime import datetime
import re
import SECLOProgressReporting as pr
from SECLODriver import SECLOCitation, SECLOLoginCredentials, SECLOFileManager, SECLOFileType, SECLORecData, SECLOInvoiceParser, SECLOCalendarParser
import logging

import os
from dotenv import load_dotenv

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME'), os.getenv('SECLO_PASSWORD'))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())

##files = SECLOFileManager(cred, 3576469)
##files.uploadRecord('bepis', True)
##files.uploadFile(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'blank.pdf')), SECLOFileType.OTHER, 'Pindonga y cuchuflito')
##print(SECLORecData(cred, 3578980).getNotificationData())
#3559053

#print(SECLORecData(cred, 3559053).getClaimData())

#print(SECLOInvoiceParser(cred).listInvoices())
#print(SECLOInvoiceParser(cred).getDetails(834))

calendar = SECLOCalendarParser(cred).getCalendar()
for entry in calendar:
    print(entry['gdeID'])
    print(entry['initDate'])
    print(entry['audID'])
    print(entry['citationDate'])
    print(SECLORecData(cred).setRecIDfromGDEID(entry['gdeID']).getClaimData())


#citation = SECLOCitation(cred, 3570278, datetime.now())
#items = citation.getItems()
#newitems = []
#for item in items:
#    if item.isEmployee():
#        item.setResult(True, 2000000)
#    print(item)
#citation.setItems(items).closeCase()

#SECLOFileManager(cred, 3570278).uploadRecord("H:\\My Drive\\133050230 Acuerdo firmado.pdf", True)


##Stuff to do
##CITATION MANAGEMENT       Done
##  NEW DATES               Done
##  CLOSE CASE              Done
##  REOPEN CASE             Done
##FILE MANAGEMENT           Done
##RECORD UPLOAD             Done
##CALENDAR PARSING          Done
##DATA PICKUP               CLOSE ENOUGH
##  CLAIM                   Done
##  NOTIFICATIONS           Done
##  CLAIM EDIT (?)          
##INVOICE PICKUP            Done

