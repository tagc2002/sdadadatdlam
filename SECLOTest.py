from datetime import datetime
import SECLOProgressReporting as pr
from SECLODriver import SECLOCitation, SECLOLoginCredentials, SECLOFileManager, SECLOFileType, SECLORecData
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
3559053

print(SECLORecData(cred, 3559053).getClaimData())

##Stuff to do
##CITATION MANAGEMENT       Done
##FILE MANAGEMENT           Done
##RECORD UPLOAD             Done
##CALENDAR PARSING          
##DATA PICKUP               
##  CLAIM                   Done
##  NOTIFICATIONS           Done
##  CLAIM EDIT (?)          
##INVOICE PICKUP            