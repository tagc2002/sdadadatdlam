from datetime import datetime
import SECLOProgressReporting as pr
from SECLODriver import SECLOCitation, SECLOLoginCredentials
import logging

import os
from dotenv import load_dotenv

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME'), os.getenv('SECLO_PASSWORD'))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler())

citation = SECLOCitation(cred, 3576469)
items = citation.getItems()
citation.setItems(items, datetime.now()).createNewCitation()