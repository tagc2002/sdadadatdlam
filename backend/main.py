import logging
from threading import Thread
from time import sleep

import os
from dotenv import load_dotenv

from repositories.SECLO.SECLODriver import SECLOLoginCredentials

load_dotenv()

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler())