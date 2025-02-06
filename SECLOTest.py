from datetime import datetime
import re
from typing import List
import backend.repositories.SECLO.SECLOProgressReporting as pr
from backend.repositories.SECLO.SECLODriver import CitationResult, SECLOCitation, SECLOLoginCredentials, SECLOFileManager, SECLOFileType, SECLORecData, SECLOInvoiceParser, SECLOCalendarParser, SECLOClaimValidationData
from backend.repositories.SECLO.SECLODataClasses import SECLOClaimData

import logging
from threading import Thread
from time import sleep

import os
from dotenv import load_dotenv

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME'), os.getenv('SECLO_PASSWORD'))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())

# files = SECLOFileManager(cred, 3576469)
# files.uploadRecord('bepis', True)
# files.uploadFile(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'blank.pdf')), SECLOFileType.OTHER, 'Pindonga y cuchuflito')
# print(SECLORecData(cred, 3578980).getNotificationData())
# 3559053




# print(SECLOInvoiceParser(cred).listInvoices())
# print(SECLOInvoiceParser(cred).getDetails(834))

#calendar = SECLOCalendarParser(cred).getCalendar()
#for entry in calendar:
#    print(entry['gdeID'])
#    print(entry['initDate'])
#    print(entry['audID'])
#    print(entry['citationDate'])
#    print('\n') 
#    print(SECLORecData(cred, 0).setRecIDfromGDEID(entry['gdeID']).getClaimData())


# gdeID = 'EX-2025-08534066'
# closeAmount = 1600000
# file = "H:\\My Drive\\08534066 Acuerdo firmado.pdf"
progress = pr.ProgressReport()
data = SECLORecData(cred, 3574262, progress)
items:List[SECLOClaimData] = []
thread = Thread(target = data.getClaimData, args = [items])
thread.start()
while(progress.getCompletion() == False):
    ans = progress.getProgress()
    if ans != None:
        print(ans)
print('OUT')
thread.join()

# for item in items:
#     if item.isEmployee():
#         item.setResult(False)
#     print(item)
# thread = Thread(target = citation.closeCase, args = [items])
# progress.setProgress(0, "")

# thread.start()
# while(progress.getCompletion() == False):
#     ans = progress.getProgress()
#     if ans != None:
#         print(ans)

# print('OUT')
# thread.join()

# filemanager = SECLOFileManager(cred, 0).setRecIDfromGDEID(gdeID)
# filemanager.uploadFile("H:\\My Drive\\08534066 DNI Trabajadora.pdf", SECLOFileType.DNI)
# filemanager.uploadFile("H:\\My Drive\\08534066 DNI Empleadora.pdf", SECLOFileType.DNI)
# filemanager.uploadFile("H:\\My Drive\\08534066 Credencial requerida.pdf", SECLOFileType.CREDENTIAL)

# filemanager.uploadRecord(file, True)

# val = SECLOClaimValidationData(cred)
# print(val.validateCUIT('27-40317985-5'))
# print(val.validateDNI('44513576'))
# print(val.validateDistrict('CAPITAL FEDERAL', ''))
# print(val.validateCounty('CAPITAL FEDERAL', 'CAPITAL FEDERAL', ''))
# print(val.validateStreet('CAPITAL FEDERAL', 'CAPITAL FEDERAL', 'CABA', 'Cerrito'))
# print(val.validateCPA('CAPITAL FEDERAL', 'CAPITAL FEDERAL', 'CABA', 'Cerrito', '628'))

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

# many items 3574262
