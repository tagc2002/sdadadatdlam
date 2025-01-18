from datetime import datetime
import SECLOProgressReporting as pr
from SECLODriver import SECLOCitation, SECLOLoginCredentials, SECLOFileManager, SECLOFileType
import logging

import os
from dotenv import load_dotenv

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME'), os.getenv('SECLO_PASSWORD'))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler())

files = SECLOFileManager(cred, 3576469)
files.uploadFile(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'blank.pdf')), SECLOFileType.OTHER, 'Pindonga y cuchuflito')