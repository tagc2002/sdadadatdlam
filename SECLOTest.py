from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
from typing import List
import backend.repositories.SECLO.SECLOProgressReporting as pr
from backend.repositories.SECLO.SECLODriver import CitationResult, SECLOCitation, SECLOLoginCredentials, SECLOFileManager, SECLOFileType, SECLORecData, SECLOInvoiceParser, SECLOCalendarParser, SECLOClaimValidationData
from backend.dataobjects.SECLODataClasses import SECLOClaimData

import logging
from threading import Thread
from time import sleep

import os
from dotenv import load_dotenv

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler())

# def progressThread(progress: pr.ProgressReport):
#     while(True):
#         ans = progress.getProgress()
#         if ans != None:
#             //print(ans)
#         if progress.getCompletion(): break


progress = pr.ProgressReport()
with SECLOCalendarParser(cred, None, progress) as cal:
    # thread = Thread(target = progressThread, args = [progress])
    # thread.start()
    items = cal.getWorkableDays()
# thread.join()
for item in items:
    print(f'{item[0].strftime('%d/%m/%Y')}:\t{item[1]} {f'({item[2]})' if not item[1] else ''}')


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


# gdeID = 'EX-2024-133692207'
# closeAmount = 4500000
# file = "H:\\My Drive\\133692207 Acuerdo firmado.pdf"

# progress = pr.ProgressReport()
# citationManager = SECLOCitation(credentials=cred, progress=progress).setRecIDfromGDEID(gdeID)
# items = citationManager.getItems()

# for item in items:
#     if item.isEmployee():
#         item.setResult(True, closeAmount)
#     print(item)
# thread = Thread(target = citationManager.closeCase, args = [items])
# progress.setProgress(0, "")

# thread.start()
# while(progress.getCompletion() == False):
#     ans = progress.getProgress()
#     if ans != None:
#         print(ans)

# print('OUT')
# thread.join()

# filemanager = SECLOFileManager(cred).setRecIDfromGDEID(gdeID)
# filemanager.uploadFile("H:\\My Drive\\133692207 Poder.pdf", SECLOFileType.PODER)
# filemanager.uploadFile("H:\\My Drive\\133692207 Credencial requerida.pdf", SECLOFileType.CREDENTIAL)

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
