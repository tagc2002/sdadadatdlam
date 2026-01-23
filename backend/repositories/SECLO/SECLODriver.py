#selenium webdriver-manager python_dotenv
from enum import Enum
from decimal import Decimal
from math import e
from pathlib import Path
import re
from time import sleep
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, InvalidElementStateException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from backend.dataobjects.enums import ClaimType
from backend.repositories.SECLO.SECLOExceptions import UnauthorizedAccessException, UnknownReportedException, RecNotAccessibleException, ValidationException, InvalidCaseStateException, InvalidParameterException, FileDownloadTimeoutException
from backend.repositories.SECLO.SECLOProgressReporting import ProgressReport
from backend.dataobjects.SECLODataClasses import SECLOAddressData, SECLOClaimData, SECLOEmployeeData, SECLOEmployerData, SECLOLawyerData, SECLONotification, SECLOOtherData, CitationResult

from datetime import datetime
from typing import List, Self, Tuple
import os
import uuid
from dotenv import load_dotenv

load_dotenv(override = True)

import logging
logger = logging.getLogger(__name__)

logging.getLogger('selenium').setLevel(logging.CRITICAL)

portalVersionSupported = '8.4.11.0'

downloadpath = Path(f'./temp/{uuid.uuid4()}')
downloadpath = downloadpath.resolve()
DEBUGMODE = os.getenv('DEBUGMODE', False)
if DEBUGMODE:
    logger.critical("\nWARNING!\n DEBUG mode enabled. Any requested changes will not be submitted.")

class SECLOLoginCredentials:
    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password

class SECLOAccessor:
    '''
    Handles the creation of the webdriver instance and auth token generation
    Other classes are meant to inherit from this.
    Provides some bullshit error handling as well, for when you get redirected to /Error.aspx.
    
    Parameters:
        credentials: Wrapper object containing login info.
        recid: claim ID to bind accessor to. Optional, but if none, must later be populated by setRecIDfromGDEID.
        progressReport: an instance of ProgressReport to display progress for long calls. 
    Returns:
        SECLOAccessor: Instance of chrome webdriver already logged in and ready for operations
    '''

    def __init__(self, credentials: SECLOLoginCredentials, recid: int | None = None, progressReport: ProgressReport | None = ProgressReport()):
        self.chrome_options = Options()
        self.chrome_options.add_experimental_option("excludeSwitches", ['enable-logging'])
        if os.getenv('HEADLESS', 'TRUE') == 'TRUE':
            logger.debug("Headless flag set true")
            self.chrome_options.add_argument('headless')
        else:
            logger.debug("Headless flag set false")

        if os.getenv('DETATCH', 'FALSE') == 'TRUE':
            self.chrome_options.add_experimental_option("detach", True)
            logger.debug("Detatch flag set true")
        else:
            logger.debug("Detatch flag set false")
        
        self.chrome_options.add_experimental_option("prefs", {
            "download.default_directory": str(downloadpath)
        })
        logger.debug(f'Download path set to {downloadpath}')

        #chrome_service.creation_flags = CREATE_NO_WINDOW
        self.credentials = credentials
        self.recid: int | None = recid
        self.progress = progressReport if (progressReport) else ProgressReport()
        return self

    def __enter__(self: Self) -> Self:
        logger.debug('Creating chrome webdriver service manager instance')
        chrome_service = ChromeService(executable_path=ChromeDriverManager().install())

        logger.debug('instantiating chrome driver')
        self.driver = webdriver.Chrome(service = chrome_service, options = self.chrome_options)
        logger.debug('Chrome loaded successfully')

        logger.debug('Getting login page...')
        for i in range(0,3):
            self.driver.get(f'https://{self.credentials.user}:{self.credentials.password}@login-int.trabajo.gob.ar/adfs/ls/wia' + \
                '?wa=wsignin1.0' + \
                '&wtrealm=https%3a%2f%2fconciliadores.trabajo.gob.ar%2f' + \
                '&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f' + \
                '&whr=https%3a%2f%2flogin-int.trabajo.gob.ar%2fadfs%2fservices%2ftrust'
            )
            try:
                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnAceptar'))).click()
                break
            except (TimeoutException, NoSuchElementException):
                if 'adfs' in self.driver.current_url:
                    raise UnauthorizedAccessException("Password is wrong or server entered inactive hours")
        logger.debug('Logged in.')
        
        try:
            WebDriverWait(self.driver,5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ColCerrar'))).click()
            logger.debug('Closed notification panel.')
        except TimeoutException as e:
            logger.debug('Notification popup not found')

        logger.info(f'Logged in as {self.driver.find_element(By.ID, "ctl00_lblConciliador").text}')
        self.portalVersion = self.driver.find_element(By.ID, "ctl00_LblAppVersion").text.split()[1]

        if (self.portalVersion != portalVersionSupported):
            logger.warning(f'Current portal version is {self.portalVersion}, but driver supports up to {portalVersionSupported}. Some features might be unexpectedly broken.')
        else: 
            logger.debug(f'Current portal version: {self.portalVersion}')
        return self
    
    def __exit__(self: Self, exception_type, exception_value, traceback):
        self.driver.quit()

    def _errorHandling(self):
        '''
        Function to handle redirects to /Error.aspx page.
        There's not much to be done other than display some boilerplate error message.
        But if its an auth problem the caller could choose to try again, so we inform this using an exception.
        '''
        try:
            if('Error.aspx' in self.driver.current_url):
                error = self.driver.find_element(By.ID, 'lblError').text
                if ('No tiene permisos para acceder a esta' in error):
                    raise UnauthorizedAccessException('SECLO Authorization error. Try initiating the request again, the token probably expired.')
                else:
                    raise UnknownReportedException('Unknown SECLO server error. Try initiating the request again.')
        except NoSuchElementException as e:
            raise InvalidElementStateException('Unknown error, most likely local. idk, man.')

    def _loadRec(self: Self):
        '''
        Receives an instance of a case searchbox and populates the hiddenRecID field to access the case.
        This method usually does not fail. Searching normally has failed a few times before.

        God I hate this shit site. 
        '''
        if self.recid == None or self.recid == 0:
            raise InvalidParameterException()
        
        logger.debug(f'Loading recID{self.recid}')
        try:
            WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
            self.driver.execute_script("arguments[0].value = "+ str(self.recid)+ ";", self.driver.find_element(By.NAME, "ctl00$Top$hdnReclamoId"))
            WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.NAME, 'ctl00$Busqueda$txtNro'))).send_keys(Keys.ENTER)
        except NoSuchElementException as e:
            logger.error("Couldn't find case searchbox element")
            raise e

    def setRecIDfromGDEID(self: Self, gdeID: str) -> Self:
        '''
        Sets the current RecID to the corresponding key for the given gdeID.

        Parameters:
            gdeID: The given gdeID to find a case. eg: "EX-2020-00000000-bullshit"
        '''

        self.progress.setSteps(1)
        self.progress.setProgress(0, "Setting recID")
        logger.debug(f'Setting recID from gdeID {gdeID}')
        self.driver.get('https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx')

        gdeYear = gdeID.split('-')[1]
        gdeFile = gdeID.split('-')[2]
        logger.debug(f'gdeYear: {gdeYear}')
        logger.debug(f'gdeFileNumber: {gdeFile}')
        try:
            findButton = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
            self.driver.find_element(By.ID, 'ctl00_Busqueda_txtNro').send_keys(gdeFile)
            self.driver.find_element(By.ID, 'ctl00_Busqueda_txtAnio').send_keys(Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.BACKSPACE+Keys.BACKSPACE+Keys.BACKSPACE+Keys.BACKSPACE+gdeYear)
            findButton.click()
        except (NoSuchElementException, TimeoutException) as e:
            logger.error("Couldn't load notifications page")
            raise e
        try:
            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdNotificaciones')))
        except NoSuchElementException as e:
            logger.error(f'Case with GDE ID {gdeID} not found')
            raise RecNotAccessibleException('Case not found')
        recID = self.driver.find_element(By.ID, 'ctl00_Top_hdnReclamoId').get_attribute('value')
        if (recID):
            self.recid = int(recID)
        else:
            raise RecNotAccessibleException("Can't load recID. bummers")
        self.progress.setCompletion("Done")
        logger.info(f'recID found, set to {self.recid}')
        return self
    
    def setGdeIdFromRecId(self: Self, recID: int) -> Self:
        '''
        Sets the corresponding GDE ID for a given case
        '''
        self.driver.get(f'https://conciliadores.trabajo.gob.ar/Conciliador_Reclamo.aspx?RecId={recID}')
        try:
            self.gdeID = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'rcNroExpediente'))).text
        except NoSuchElementException:
            logger.error("Case not found")
        return self


class SECLOCitation(SECLOAccessor):
    '''
    A browser driver class to register citation results on the SECLO site. 
    Used for creating a new citation or closing a case with or without agreement.
    Most methods return self for easy chaining.
    eg. citation= SECLOCitation().setRecIDfromGDEID().reopenCase().getItems()
        citation.closeCase()
        citation.createNewCitation()
    
    Parameters:
        credentials(SECLOLoginCredentials): The credential instance to authorize the requests.
        recid (int | None): The recID to set for this instance. Can be set to None if it will be later set by gdeID, but it cant be none when actually loading.
        date (datetime): The presentation date to set for the result form. Current date by default.
        progress: Instance of ProgressReport to report progress on blocking functions. 
    '''
    def __init__(self, credentials: SECLOLoginCredentials, recid: int | None = None, date: datetime = datetime.now(), progress: ProgressReport | None = None):
        super().__init__(credentials, recid, progressReport = progress)
        logger.info(f'Created SECLOCitation with recid {str(recid)}{". Must set manually using gdeID before proceeding, lest you risk an exception" if recid == None or recid == 0 else ''}')
        
        self.date = date
        self.error = None

    def __loadCitationResultScreen(self: Self) -> None:
        '''
        Loads the first screen of the result form (aka selecting agreement/non-agreement)
        '''
        logger.debug(f'Accessing citation result window')
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_btnAudiencia'))).click()
        self._loadRec()
        try:
            if ('Registrar Resultado Audiencia' in WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_tb'))).find_elements(By.CLASS_NAME, 'appBoxMenuTitle')[1].text):
                if (self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos').get_attribute('disabled')):
                    logger.debug('Claim object comb selector is disabled. This is good.')
                    self.multiple = False
                else:
                    logger.debug('Claim object comb selector is enabled. This will be a bummer')
                    self.multiple = True
                    self.combSelectorLength = len(Select(self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos')).options)
                    self.combSelectorIndex = 0
        except Exception as e:
            raise RecNotAccessibleException(f'Could not access result form for rec {self.recid}. Maybe its closed.')

    def reopenCase(self: Self) -> Self:
        '''
        Reopens a given case. Does not verify if its closed, thats the responsibility of the caller.
        '''
        logger.debug(f'Attempting to reopen case {self.recid}')
        self.progress.setSteps(2)
        self.progress.setProgress(0, "Loading case for reopening")

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkReabrir'))).click()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
        self._loadRec()
        self.progress.increaseProgress(1, "Reopening case")
        try:
            self.driver.find_element(By.ID, 'ctl00_Busqueda_grdReclamos')   #if present, case was not found
        except NoSuchElementException:
            pass
        else:
            raise InvalidCaseStateException("Case not found, probably its still open")
        
        reopenButton = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnReabrir')))
        logger.debug("Reopen button found")
        try:
            error = self.driver.find_element(By.ID, 'ctl00_Center_lblmensaje').text
        except NoSuchElementException:
            pass
        else:
            if error:
                raise InvalidCaseStateException(error)
        if not DEBUGMODE:
            reopenButton.click()
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        else:
            logger.critical("DEBUG MODE WON'T SUBMIT REOPENING REQUEST")
        self.progress.setCompletion("Done reopening")
        return self

    def getItems(self: Self) -> List[CitationResult]:
        '''
        Gets the current list of employees and employers registered in this claim.
        Modify this list with the results and new notification if needed and send it to setItems.

        Returns:
            set[CitationResult]: A set containing all the involved parts in the case. 
                This set must later be populated by the caller with result and notification 
                information and fed to closeCase() or createNewCitation().
        '''
        self.progress.setSteps(2)
        logger.info('Performing Citation getItems')
        self.progress.setProgress(0, "Loading case")
        self.__loadCitationResultScreen()
        self.fields = []
        self.fieldsLen = 0
        logger.debug('Case attained')

        self.progress.increaseProgress(1, "Loading items")
        try:
            table = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')))
            for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
                self.fields.append(CitationResult(row, True))
                self.fields.append(CitationResult(row, False))
                self.fieldsLen += 1
            self.fields = set(self.fields)
            logger.debug(f'Found the following people in this citation:')
            for field in self.fields:
                logger.debug(field)
            self.progress.setCompletion("Done getting items.")
            items = []
            for item in self.fields:
                items.append(item)
            return items
        except Exception as e:
            raise InvalidCaseStateException(f'Something happenned loading the result fields.\n{e}')

    def __rowPopulatedCheck(self: Self, row: WebElement) -> bool:
        '''
        Checks whether a row from citation result screen is populated already.

        Parameters:
        row(WebElement): A table row selected from the result screen
        '''
        return (not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked") 
                and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked"))

    def __setItems(self: Self, ignoreMultipleComb) -> Self:
        logger.info('Performing Citation getItems')
        self.__loadCitationResultScreen()
        
        if self.multiple:
            if self.combSelectorIndex == self.combSelectorLength:
                logger.debug("Done setting items.")
                return self.__advanceResultForm()
            else:
                Select(WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_cmbObjetos')))).select_by_index(self.combSelectorIndex)
                logger.debug(f'Selected comb level entry {self.combSelectorIndex + 1} of {self.combSelectorLength}')
                self.combSelectorIndex += 1     
        self.progress.setSteps(1 + ((1 if ignoreMultipleComb or not self.multiple else self.combSelectorLength) * (self.fieldsLen + 1)))     
        try:
            for entry in set(self.items):
                if not entry.isEmployee():
                    continue
                loop = True
                while loop:
                    loop = False
                    logger.info('Getting table contents')
                    table = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')))
                    for i, row in enumerate(table.find_elements(By.CLASS_NAME, 'grdRowStyle')):
                        if (CitationResult(row) == entry 
                            and self.__rowPopulatedCheck(row)
                            and entry.enabled and CitationResult(row).enabled
                        ):
                            self.progress.increaseProgress(1, "Setting results...")  
                            logger.debug(f'Row {i} matches entry {entry} and is unselected, applying...')
                            logger.debug(f'({row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked")} {row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked")})')
                            if (entry.amount):
                                #set agreement
                                logger.info(f'Agreement for {entry}')
                                row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'label').click()
                                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnSeguir4')))
                                loop = True
                                for row2 in self.driver.find_element(By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos').find_elements(By.CLASS_NAME, 'grdRowStyle'):
                                    if (row2.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute('checked') and 
                                        len(row2.find_elements(By.TAG_NAME, 'td')[4].find_element(By.TAG_NAME, 'input').text) == 0
                                        ):
                                            row2.find_elements(By.XPATH, './*')[4].find_element(By.TAG_NAME, 'input').send_keys(entry.amount.replace('.',','))
                                            break
                                else:
                                    raise InvalidCaseStateException("Couldn't find amount input for last case result")
                            else:
                                #set non-agreement
                                logger.info(f'Non-agreement for {entry}')
                                row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').click()
                                loop = True
                                break
        except Exception:
            self._errorHandling()
        for row in WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos'))).find_elements(By.CLASS_NAME, 'grdRowStyle'):
            if(self.__rowPopulatedCheck(row)):
                raise InvalidElementStateException('Incomplete selection')
        return self.__advanceResultForm()
    
    def __fillDateInput(self: Self, inputID: str, date: datetime):
        logger.info(self.date.strftime('%d%m%Y'))
        datefield = self.driver.find_element(By.ID, inputID)
        for i in range(0, 10):
            datefield.send_keys(Keys.ARROW_LEFT)
        datefield.send_keys(date.strftime('%d%m%Y'))   
                 
    def __advanceResultForm(self: Self):
        try:
            self.__fillDateInput("ctl00_Center_txtFecha_txtFecha", self.date)          
            self.driver.find_element(By.ID, 'ctl00_Center_btnSeguir4').click()
        except Exception as e:
            logger.error(f'error submitting form \n{e}')
            raise e
        self.__validationErrorChecker()
        return self

    
    def __validationErrorChecker(self: Self):
        try:
            self.error = self.driver.find_element(By.CLASS_NAME, 'ctl00_Center_lblError').text
        except NoSuchElementException as e:
            pass
        except Exception as e:
            logger.warning(f'Unknown error encountered checking for errors\n{e}')
        else:
            raise ValidationException(self.error)
        
        try:
            del self.error
            self.error = self.driver.find_element(By.CLASS_NAME, 'ctl00_Center_ValidationSummary5').text
        except NoSuchElementException as e:
            pass
        except Exception as e:
            logger.warning(f'Unknown error encountered checking for errors\n{e}')
        else:
            raise ValidationException(self.error)
    
    def createNewCitation(self: Self, items: set[CitationResult], date: datetime):  
        '''
        Receives a modified items set with the appropiate result and notification data, plus a date, and registers a new citation.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (set[CitationResult]): The set provided by getItems with the proper result and notification attributes set.
            date: The date and time requested for the new citation.
        '''
        self.items = items
        self.__setItems(True)  
        absentCitation = False
        self.progress.increaseProgress(1, "Setting new citation date")
        for item in self.items:
            if item.absent:
                absentCitation = True
        if absentCitation:
            self.driver.find_element(By.ID, 'ctl00_Center_btnNuevaIncomparecencia').click()
        else:
            self.driver.find_element(By.ID, 'ctl00_Center_btnNuevaAudiencia').click()
        self.__fillDateInput('ctl00$Center$txtFecha$txtFecha', date)
        Select(self.driver.find_element(By.ID, 'ctl00_Center_cmbHoras')).select_by_visible_text(f'{date.hour:02}')
        Select(self.driver.find_element(By.ID, 'ctl00_Center_cmbMinutos')).select_by_visible_text(f'{(date.minute - date.minute % 5):02}')
      
        for row in self.driver.find_element(By.ID, 'ctl00_Center_grdTrabajadores').find_elements(By.CLASS_NAME, 'grdRowStyle'):
            for entry in self.items:
                if row.find_elements(By.TAG_NAME, 'td')[0].text in entry.getPerson() and row.find_elements(By.TAG_NAME, 'td')[1].text in entry.getPerson():
                    if (entry.absent):
                        row.find_elements(By.TAG_NAME, 'td')[2].find_element(By.TAG_NAME, 'input').click()
                    if (entry.notify):
                        if absentCitation:
                            row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input').click()
                        Select(row.find_elements(By.TAG_NAME, 'td')[4 if absentCitation else 2].find_element(By.TAG_NAME, 'select')).select_by_value(entry.notificationMethod.value)
                    break
        for row in self.driver.find_element(By.ID, 'ctl00_Center_grdEmpleadores').find_elements(By.CLASS_NAME, 'grdRowStyle'):
            for entry in self.items:
                if row.find_elements(By.TAG_NAME, 'td')[0].text in entry.getPerson():
                    if (entry.absent):
                        row.find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').click()
                    if (entry.notify):
                        if absentCitation:
                            row.find_elements(By.TAG_NAME, 'td')[2].find_element(By.TAG_NAME, 'input').click()
                        Select(row.find_elements(By.TAG_NAME, 'td')[3 if absentCitation else 1].find_element(By.TAG_NAME, 'select')).select_by_value(entry.notificationMethod.value)

        if not DEBUGMODE:
            self.driver.find_element(By.ID, 'ctl00_Center_btnGrabar').click()
            self.__validationErrorChecker()
        else:
            logger.critical("DEBUG MODE WON'T PERSIST NEW CITATION. However, this citation will be marked as 'completed' rather than 'pending', to allow verifying this last stage")
        self.progress.setCompletion("Done new citation request")

    def closeCase(self: Self, items: set[CitationResult]):
        '''
        Sets the claim results based on the items and then closes the case.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (set[CitationResult]): The modified set of items provided by getItems, with the results set.
        '''
        self.items = items
        if (self.multiple):
            while(self.combSelectorIndex < self.combSelectorLength):
                self.__setItems(False)
                self.progress.increaseProgress(1, "Closing partial claim")
                if not DEBUGMODE:
                    self.driver.find_element(By.ID, 'ctl00_Center_btnGrabarTotal').click()
                    WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                    self.driver.switch_to.alert.accept()
        else:
            self.__setItems(False)
            self.progress.increaseProgress(1, "Closing claim")
            if not DEBUGMODE:
                self.driver.find_element(By.ID, 'ctl00_Center_btnGrabarTotal').click()
                WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                self.driver.switch_to.alert.accept()
            else: 
                logger.critical("DEBUG MODE WON'T SUBMIT CLOSE REQUEST.")
        self.progress.setCompletion("Done closing claim")

class SECLOFileType(Enum):
    PODER = ('18', False)
    DNI = ('20', False)
    OTHER = ('21', True)
    CREDENTIAL = ('33', False)
    AUTH = ('34', False)
    SIGNED = ('36', False)

class SECLOFileManager(SECLOAccessor):
    '''
    A class to handle file management, including querying and downloading already present files, uploading new ones, or uploading records.

    Parameters:
        credentials: The wrapper object containing the login information.
        recid: Tha claim number to bind to this instance.
    '''
    def __init__(self: Self, credentials: SECLOLoginCredentials, recid: int | None = None):
        super().__init__(credentials, recid)
        self.__getFiles()

    def __getFiles(self: Self):
        '''
        Populates internal object storage with the current files in rec.
        idc about congruency, this is a throwaway object that expires quickly.
        '''
        self.driver.get(f'https://conciliadores.trabajo.gob.ar/Documentacion_Adjunta.aspx?RecId={self.recid}')
        files: List[Tuple[str, str, datetime]] = []
        for row in self.driver.find_element(By.ID, 'grdDocumentos').find_elements(By.CLASS_NAME, 'grdRowStyle'):
            files.append((
                row.find_elements(By.TAG_NAME, 'td')[0].text,
                row.find_elements(By.TAG_NAME, 'td')[1].text,
                self.__shitDateToDatetime(
                    row.find_elements(By.TAG_NAME, 'td')[2].text
                )
            ))
            logger.debug(files[-1])
        self.fileList = files

    def getFiles(self: Self) -> List[Tuple[str, str, datetime]]:
        '''
        Gets a list of all the registered files currently uploaded to this rec.
        
        Returns: 
            files (Tuple[str, str, datetime]): (type, description, date)
        '''
        return self.fileList[:]
    
    def getFile(self: Self, index: int) -> Path:
        '''
        Request a given file from the list of uploaded file.

        Parameters:
            index (int): The index of the requested file
        Returns:
            Nothing currently, but hopefully later a handle to the downloaded file. It's downloaded to a temp directory so you can go look for it tho.
        '''

        if index >= len(self.fileList) or index < 0:
            raise IndexError("Requesting a file beyond bounds")
        self.getFiles()
        logger.debug("Downloading file")
        download = self.driver.find_element(By.ID, 'grdDocumentos').find_elements(By.CLASS_NAME, 'grdRowStyle')[index].find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input')
        logger.info(download.get_attribute("title"))
        downloadfile = downloadpath / 'Reporte.pdf' #Hardcoded name (for this page at least) Selenium doesn't really offer a solution for downloading files.
        downloadfile.unlink(True)   
        download.click()
        for i in range(0, 200):
            if downloadfile.exists():
                return downloadfile
            else:
                sleep(0.1)
        else:
            raise FileDownloadTimeoutException("Timeout while trying to download file, try again later.")

    def uploadFile(self: Self, file: str, filetype: SECLOFileType, description: str | None = None) -> None:
        '''
        Uploads a file. Works for everything except records, which are uploaded using the uploadRecord method because its completely different for some godforsaken reason.
        Parameters:
            file (str): The path to the file to be uploaded. Must be a PDF.
            filetype: The given filetype to upload, from the enum.
            description: Only used when uploading a 'other' type of file. 
        '''
        self.driver.get(f'https://conciliadores.trabajo.gob.ar/Documentacion_ParaAdjuntar.aspx?RecId={self.recid}')

        Select(WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.ID, 'Tipo_Documentacion')))).select_by_value(filetype.value[0])
        if filetype.value[1] == True:
            if description is None:
                raise InvalidParameterException("Description cannot be null for this type of file")
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'txtDescripcion'))).send_keys(description)
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'Archivo'))).send_keys(file)
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'btnAgregar'))).click()

        # Save button (why tf is it unlabeled?? This is some lousy website coding)
        if not DEBUGMODE:
            save = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'Button1')))
            save.click()
            WebDriverWait(self.driver, 5).until(EC.staleness_of(save))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'Button1')))

            errorStr = self.driver.find_element(By.CLASS_NAME, 'ingreso').find_elements(By.TAG_NAME, 'tr')[1].text.strip()
            if errorStr:
                raise ValidationException(f'Error uploading file: {errorStr}')
        else:
            logger.warning("FILE WON'T BE SAVED IN DEBUG MODE!")
        self.__getFiles()
    
    def uploadRecord(self: Self, file: str, agreement: bool) -> None:
        '''
        Uploads a record to an already closed case.
        Parameters:
            file (str): Path to the desired record to upload.
            agreement (bool): Whether its an agreement or not, because the way of uploading them is different for some godforsaken reason. 
        '''
        if (self.recid):
            self.setGdeIdFromRecId(self.recid)
        else:
            raise InvalidParameterException("Missing recID")
        logger.info(self.gdeID)
        
        self.driver.get('https://conciliadores.trabajo.gob.ar/Novedades.aspx')
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_btnActa'))).click()
        loadNextPage = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnBuscar')))
        if agreement:
            self.driver.find_element(By.ID, 'ctl00_Center_radTipo_0').click()
        else:
            self.driver.find_element(By.ID, 'ctl00_Center_radTipo_1').click()
        loadNextPage.click()

        table = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_grdReclamos')))
        try:
            list = table.find_elements(By.CLASS_NAME, 'grdRowStyle')
        except NoSuchElementException:
            raise InvalidElementStateException("There are no elements available to upload records here. That sucks, man.")
        
        for row in list:
            if row.find_elements(By.TAG_NAME, 'td')[0].text.strip() == self.gdeID:
                #TODO verify if record has already been uploaded
                #I need the site to have a pending case to upload, so later
                row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input').send_keys(file)
                found = True
                break  
        else:
            raise InvalidElementStateException("Given claim does not have record uploading enabled right now.")
        
        if not DEBUGMODE:
            self.driver.find_element(By.ID, 'ctl00_Center_btnGenerar').click()
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_grdReclamos')))
        else: 
            logger.warning("WON'T UPLOAD RECORD IN UPLOAD MODE!")
        return

    def __shitDateToDatetime(self: Self, date: str) -> datetime:
        '''
        receives a date in a weird ugly format like 30/dic./2024
        and returns a proper datetime object for it
        my god i hate this      
        '''
        day = int(date.split('/')[0])
        month = date.split('/')[1]
        newMonth = 1
        year = int(date.split('/')[2])
        if 'ene' in month:
            newMonth = 1
        elif 'feb' in month:
            newMonth = 2
        elif 'mar' in month:
            newMonth = 3
        elif 'abr' in month:
            newMonth = 4
        elif 'may' in month:
            newMonth = 5
        elif 'jun' in month:
            newMonth = 6
        elif 'jul' in month:
            newMonth = 7
        elif 'ago' in month:
            newMonth = 8
        elif 'sep' in month:
            newMonth = 9
        elif 'oct' in month:
            newMonth = 10        
        elif 'nov' in month:
            newMonth = 11
        elif 'dic' in month:
            newMonth = 12
        return datetime(day = day, month = newMonth, year = year)

class SECLORecData(SECLOAccessor):
    '''
    A class for accessing data from claims, the main data ingestion class if you may. 
    Eventually may allow modifying data as well, but the website is so shit I don't think it'll be reliable.
    '''
    def getNotificationData(self: Self) -> List[dict]:
        '''
        Gets the associated notification information for a given case. Its up to the caller to link those to a citation or stuff like that.

        Returns:
            List[dict]: The list of notification entries. 
        '''
        self.driver.get('https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx')
        self._loadRec()

        results = []
        table = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_Center_grdNotificaciones')))
        for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
            results.append({
                'id': row.find_elements(By.TAG_NAME, 'td')[0].text,
                'person': row.find_elements(By.TAG_NAME, 'td')[1].text,
                'citationType': row.find_elements(By.TAG_NAME, 'td')[2].text,
                'employer': True if row.find_elements(By.TAG_NAME, 'td')[3].text == 'Emp' else False,
                'notificationType': SECLONotification.NotificationShortToEnum(row.find_elements(By.TAG_NAME, 'td')[4].text),
                'generatedDate': datetime.strptime(row.find_elements(By.TAG_NAME, 'td')[5].text, '%d/%m/%Y'),
                'notifiedDate': None if len(row.find_elements(By.TAG_NAME, 'td')[6].text) == 0 
                                else datetime.strptime(row.find_elements(By.TAG_NAME, 'td')[6].text, '%d/%m/%Y'),
                'notificationCode': row.find_elements(By.TAG_NAME, 'td')[7].text,
                'notificationStatus': row.find_elements(By.TAG_NAME, 'td')[8].text,
                'afipRead': row.find_elements(By.TAG_NAME, 'td')[9].text,
                'citationDate': datetime.strptime(row.find_elements(By.TAG_NAME, 'td')[10].text, '%d/%m/%Y %H:%M'),
                'citationStatus': row.find_elements(By.TAG_NAME, 'td')[11].text,
            })
        return results

    def getClaimData(self: Self) -> SECLOClaimData:
        '''
        Accesses the given claims initiation data. Useful to get names, IDs, employment parameters, etc. 
        
        Returns:
            SECLOClaimData: an object that contains all claim data.
        '''
        self.progress.setSteps(1)
        self.progress.setProgress(0, "Loading claim data form...")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkModificacion'))).click()
        self._loadRec()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ucReclamo_txtFecha')))
        seclodbOK = True
        totalItems = len(self.driver.find_element(By.ID, 'ctl00_Center_lstTrabajadores').find_elements(By.TAG_NAME, 'li'))
        totalItems += len(self.driver.find_element(By.ID, 'ctl00_Center_lstEmpleadores').find_elements(By.TAG_NAME, 'li'))
        totalItems += len(self.driver.find_element(By.ID, 'ctl00_Center_lstReprentantes').find_elements(By.TAG_NAME, 'li'))
        try:
            totalItems += len(self.driver.find_element(By.ID, 'ctl00_Center_lstDerechohabientes').find_elements(By.TAG_NAME, 'li'))
        except NoSuchElementException:
            pass
        self.progress.setSteps(2 + totalItems)
        #CLAIM
        self.progress.increaseProgress(1, "Getting claim data...")
        claimData = SECLOClaimData(
            recid = self.recid or 0,
            legalStuff = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_txtComentario').get_attribute('value') or "",
            initWorker = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_optReclamante_0').get_attribute('checked') == True
        )
        for row in self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_chkObjetoReclamo').find_elements(By.TAG_NAME, 'td'):
            if row.find_element(By.TAG_NAME, 'input').get_attribute('checked'):
                claimData.addClaimObject(ClaimType.stringToEnum(row.find_element(By.TAG_NAME, 'label').text))
        
        #EMPLOYEES
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstTrabajadores').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstTrabajadores')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()
            
            cuil = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl00_cuit_txtC')))
            name = f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtApellido_txt').get_attribute('value') or ""} {self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNombre_txt').get_attribute('value') or ""}'
            self.progress.increaseProgress(1, f'Getting worker data for {name} ({i + 1} of {listLen})...')

            if len(cuil.text) > 0 and seclodbOK and not cuil.get_attribute('disabled'):
                cuil.click()
                cuil.send_keys(Keys.TAB)
                WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value') or "") > 0)
                if 'null null' not in (self.driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value') or ""):
                    name = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value') or ""
                else:
                    seclodbOK = False
            employee = SECLOEmployeeData(
                name = name,
                dni = int(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS').get_attribute('value') or "0"),
                cuil = int((cuil.get_attribute('value') or "").replace('-', '')),
                validated = seclodbOK
            )
            employee.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtProvincia').get_attribute('value') or "",
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtPartido').get_attribute('value') or "",
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtLocalidad').get_attribute('value') or "",
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtCalle').get_attribute('value') or "",
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtDepart').get_attribute('value'),
                    cpa=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )
            employee.addBirthDate(datetime.strptime(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecNacimiento_txt').get_attribute('value') or "", "%d/%m/%Y"))
            employee.addClaimAmount(int(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtImporte_txt').get_attribute('value') or ""))
            employee.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtEmail_txt').get_attribute('value'))
            employee.addMobilePhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCodArea_Numerico').get_attribute('value') or "", self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCel_Numerico').get_attribute('value') or "")
            employee.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtTelefono_txt').get_attribute('value'))
            employee.addStartDate(datetime.strptime(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecIngreso_txt').get_attribute('value') or "", "%d/%m/%Y"))
            employee.addEndDate(datetime.strptime(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecEgreso_txt').get_attribute('value') or "", "%d/%m/%Y"))
            employee.addType(cct = int(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtConvenioNum_txt').get_attribute('value') or ""), category = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCategoria_txt').get_attribute('value'))
            employee.addWage(int(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtRemuneracion_txt').get_attribute('value') or ""))
            claimData.addEmployee(employee)
            if seclodbOK:
                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl00_btnAgregar'))).click()
            i += 1

        #EMPLOYERS
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstEmpleadores').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstEmpleadores')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()

            WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl01_cuit_txtRS')))
            self.progress.increaseProgress(1, f'Getting employer data for {self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtRS').get_attribute('value')} ({i + 1} of {listLen})...')
            employer = SECLOEmployerData(
                name=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtRS').get_attribute('value') or "",
                dni=int(self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtNroDocumento_txt').get_attribute('value') or "0"),
                cuil=int((self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtC').get_attribute('value') or "0").replace('-','')),
                validated = seclodbOK
            )
            employer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtProvincia').get_attribute('value') or "",
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPartido').get_attribute('value') or "",
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtLocalidad').get_attribute('value') or "",
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCalle').get_attribute('value') or "",
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtDepart').get_attribute('value'),
                    cpa=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )
            employer.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtTelefono_txt').get_attribute('value'))
            for item in self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cmbTipoSociedad_cmb').find_elements(By.TAG_NAME, 'option'):
                if item.get_attribute('selected'):
                    employer.addPersonType(item.text)
            employer.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtTelefono_txt').get_attribute('value'))
            claimData.addEmployer(employer)
            if seclodbOK:
                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_btnAgregar'))).click()
            i += 1
        
        #LAWYERS
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstReprentantes').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstReprentantes')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()

            email = (self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtEmail_txt').get_attribute('value') or "").strip()
            phone = self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtTelefono_txt').get_attribute('value')
            mobileprefix = self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtCodArea_Numerico').get_attribute('value')
            mobilephone = self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtCel_Numerico').get_attribute('value')

            #name validation
            folio = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl02_txtFolio_txt')))
            foliovalue = folio.get_property('value')
            folio.send_keys(Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + '0' + Keys.TAB)
            WebDriverWait(self.driver, 5).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            folio.send_keys(str(foliovalue))
            folio.send_keys(Keys.TAB)
            WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text) > 0)
            self.progress.increaseProgress(1, f'Getting lawyer data for {self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text} {self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtApellido_lbl').text} ({i + 1} of {listLen})...')

            lawyer = SECLOLawyerData(
                name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text} {self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtApellido_lbl').text}',
                dni=int(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNroDocumento_lbl').text),
                validated = seclodbOK
            )
            lawyer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtProvincia').get_attribute('value') or "",
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPartido').get_attribute('value') or "",
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtLocalidad').get_attribute('value') or "",
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtCalle').get_attribute('value') or "",
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtDepart').get_attribute('value'),
                    cpa=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )

            for row in self.driver.find_element(By.ID, 'ctl00_Center_ctl02_lstAsignados').find_elements(By.TAG_NAME, 'td'):
                if row.find_element(By.TAG_NAME, 'input').get_attribute('checked'):
                    name = row.text.replace(',', '')
                    lawyer.addRepresented(
                        isEmployee=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_chkRepresentantes_0').get_attribute('checked') == True, 
                        name=name
                    )
            lawyer.addPhone(phone)
            lawyer.addMobilePhone(prefix=mobileprefix or "", phone=mobilephone or "")
            lawyer.addMail(email)
            lawyer.addTF(int(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtTomo_txt').get_attribute('value') or "0"), int(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtFolio_txt').get_attribute('value') or "0"))
            claimData.addLawyer(lawyer)
            i += 1       
        
        #OTHERS
        try:
            listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstDerechohabientes').find_elements(By.TAG_NAME, 'li'))
        except NoSuchElementException:
            pass
        else:
            i = 0
            while i < listLen:
                list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstDerechohabientes')))
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()
                WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl03_txtNombre_txt')))
                self.progress.increaseProgress(1, f'Getting other data for {self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNombre_txt').get_attribute('value')} ({i + 1} of {listLen})...')
                other = SECLOOtherData(
                    name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNombre_txt').get_attribute('value')}',
                    dni=int(self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNroDocumento_txt').get_attribute('value') or "0"),
                )
                other.addAddress(
                    SECLOAddressData(
                        province=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtProvincia').get_attribute('value') or "",
                        district=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtPartido').get_attribute('value') or "",
                        county=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtLocalidad').get_attribute('value') or "",
                        street=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtCalle').get_attribute('value') or "",
                        number=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtNumero').get_attribute('value'),
                        floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtPiso').get_attribute('value'),
                        apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtDepart').get_attribute('value'),
                        cpa=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtCPA').get_attribute('value'),
                        bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtAdicional').get_attribute('value')
                    )
                )
                other.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtEmail_txt').get_attribute('value'))
                other.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtTelefono_txt').get_attribute('value'))
                other.addMobilePhone(prefix=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtCodArea_Numerico').get_attribute('value') or "", phone=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtCel_Numerico').get_attribute('value') or "")
                claimData.addOther(other)
                i += 1

        #END
        self.progress.setCompletion("Done getting data.")
        if seclodbOK and not DEBUGMODE:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lnkFinalizar'))).click()
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnAceptarRec'))).click()
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnSi'))).click()
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        return claimData

    def __addressFieldComplete(self: Self, field: WebElement, text: str) -> None:
        if not field.get_attribute('readOnly'):
            field.send_keys(text)
            WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ui-widget-content')))
            field.send_keys(Keys.ENTER + Keys.TAB)
            try:
                errorTxt = WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.CLASS_NAME, 'divMensajeWarning'))).text
                raise InvalidCaseStateException(f'Address error: {errorTxt}')
            except (NoSuchElementException, TimeoutException):
                pass    #expected
    
    def addEmployer(self: Self, employer: SECLOEmployerData)-> Self:
        '''
        Ettempts to expand a claim with the given employer. This can fail in many many ways, but we can try at least.
        Parameters:
            employer (SECLOEmployerData): The employer to be added.
        '''
        self.progress.setSteps(1)
        self.progress.setProgress(0, "Loading claim data form...")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkModificacion'))).click()
        self._loadRec()
        for i in range(0, 5):
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ucReclamo_txtFecha')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lnkEmpleadores'))).click()
            cuitBox = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_cuit_txtC')))
            if cuitBox.is_enabled():
                break
        else:
            raise InvalidCaseStateException("Couldn't open employer edit menu, you might need to edit this manually")
    
        Select(WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_cmbTipoSociedad_cmb')))).select_by_visible_text(employer.personType)
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_cuit_txtC'))).send_keys(str(employer.cuil) + Keys.TAB)
        Select(WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_cmbActividad_cmb')))).select_by_value("22") #Otra
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_txtActividad_txt'))).send_keys('alguna actividad misteriosa de la cual desconocemos' + Keys.TAB)    

        self.__addressFieldComplete(WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtProvincia'))), employer.address.province if employer.address else "")
        self.__addressFieldComplete(WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPartido'))), employer.address.district if employer.address else "")
        self.__addressFieldComplete(WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtLocalidad'))), employer.address.county if employer.address else "")
        self.__addressFieldComplete(WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCalle'))), employer.address.street if employer.address else "")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtNumero'))).send_keys(((employer.address.number if employer.address else "") or "") + Keys.TAB)
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPiso'))).send_keys((employer.address.floor if employer.address else "") or "")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtDepart'))).send_keys((employer.address.apt if employer.address else "") or "")
        cpa = WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCPA')))
        if not cpa.get_attribute('value'):
            cpa.send_keys((employer.address.cpa if employer.address else "") or "")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtAdicional'))).send_keys((employer.address.bonusData  if employer.address else "") or "")

        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_txtEmail_txt'))).send_keys(employer.mail or "")
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_txtTelefono_txt'))).send_keys(employer.phone or "")

        if not DEBUGMODE:
            WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_btnAgregar'))).click()
            WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_btnAgregar')))
            errorText = self.driver.find_element(By.ID, 'ctl00_Center_ctl01_ValidationSummary1').text.strip()
            if errorText:
                raise InvalidCaseStateException(errorText)

        return self
    
class SECLOInvoiceParser(SECLOAccessor):
    def listInvoices(self: Self):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkConsultaLiquidacion'))).click()
        invoices = []
        for option in WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_cmbLiquidaciones'))).find_elements(By.TAG_NAME, 'option'):
            invoices.append({'id': int(option.get_attribute('value') or 0), 'date':datetime.strptime(option.text.split()[0], "%d/%m/%Y")})
        return invoices
    
    def getDetails(self: Self, invoice: int):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkConsultaLiquidacion'))).click()
        Select(WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_cmbLiquidaciones')))).select_by_value(str(invoice))
        self.driver.find_element(By.ID, 'ctl00_Center_btnBuscar').click()

        result = []
        table = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdMovimientos')))
        for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
            result.append(
                {
                    'gdeID': row.find_elements(By.TAG_NAME, 'td')[2].text,
                    'amount': Decimal(row.find_elements(By.TAG_NAME, 'td')[4].text[2:-1].replace('.','').replace(',','.')),
                    'date': datetime.strptime(row.find_elements(By.TAG_NAME, 'td')[5].text, "%d/%m/%Y")
                 }
                )
        return {
                'total': Decimal(self.driver.find_element(By.ID, 'ctl00_Center_lblTotal').text.split()[1].replace(',','.')), 
                'detail': result
            }

class SECLOCalendarParser(SECLOAccessor):
    def getCalendar(self: Self):
        '''
        Fetches the current calendar assignments from SECLO. Ideal entry point for claim registration and validating cases
        '''
        WEEKS = 20
        firstStage = ProgressReport().setSteps(1 + WEEKS).setMessage("Loading calendar")
        secondStage = ProgressReport()
        self.progress.compose(firstStage).compose(secondStage)
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_btnAgenda'))).click()

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_chkSusp'))).click()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_chkReal'))).click()

        #Loop through weeks
        IDs = []
        for i in range(0, WEEKS):
            firstStage.increaseProgress(1, f'Parsing calendar week {i} of {WEEKS}')
            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_DayPilotCalendar1')))
            table = self.driver.find_element(By.ID, 'ctl00_Center_DayPilotCalendar1').find_element(By.TAG_NAME, 'tr')
            #loop through days
            for day in table.find_elements(By.TAG_NAME, 'table')[1].find_elements(By.TAG_NAME, 'tr')[0].find_elements(By.TAG_NAME, 'td'):
                #loop through cases in day
                for case in day.find_element(By.TAG_NAME, 'div').find_elements(By.TAG_NAME, 'div'):
                    foundID = str(case.get_attribute('onclick'))
                    if foundID:
                        foundID = re.search(r'PK:\d+', foundID)
                        if foundID:
                            IDs.append(foundID.group(0)[3:])
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lnkDer'))).click()
        secondStage.setSteps(len(IDs))
        secondStage.setMessage("Loading citation data")
        firstStage.setCompletion("Finished loading calendar weeks")
        calendarCitations = []
        for index, item in enumerate(IDs):
            secondStage.increaseProgress(1, f'Loading citation data for {index + 1} of {len(IDs)}')
            self.driver.get(f'https://conciliadores.trabajo.gob.ar/Conciliador_Audiencia.aspx?AudId={item}&esPortal=1')
            gdeIDText = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'rcNroExpediente'))).text
            initDatetimeText = self.driver.find_element(By.ID, 'rcFecha').text
            initDateTimeText = initDatetimeText.split()[0] + ' ' + initDatetimeText.split()[1].split(':')[0] + ':' + initDatetimeText.split()[1].split(':')[1]
            calendarCitations.append(
                {'gdeID': gdeIDText,
                 'citationDate': datetime.strptime(self.driver.find_element(By.ID, 'rcFechaA').text.split('a')[0], r'%d/%m/%Y - %H:%M '),
                 'initDate': datetime.strptime(initDateTimeText, r'%d/%m/%Y %H:%M'),
                 'citationID': item,
                 'citationType': self.driver.find_element(By.ID, 'auTipoYEstado').text
                })
        secondStage.setCompletion("Finished loading calendar info")
        return calendarCitations

class SECLOClaimValidationData(SECLOAccessor):
    def _createRequest(self: Self, endpoint: str, data: str):
        cookies = {}
        cookieList = self.driver.get_cookies()
        for cookie in cookieList:
            cookies[cookie['name']] = cookie['value']
        ua = self.driver.execute_script("return navigator.userAgent")
        headers= {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'es-419,es-US;q=0.9,es;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'conciliadores.trabajo.gob.ar',
            'Origin': 'https://conciliadores.trabajo.gob.ar',
            'Refererer': 'https://conciliadores.trabajo.gob.ar/ingresoreclamos.aspx',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': ua,
            'X-Requested-With': 'XMLHttpRequest'
        }
        print(cookies)
        req = requests.Request('POST', endpoint, data=data, headers=headers, cookies=cookies)
        req = req.prepare()
        print('{}\n{}\r\n{}\r\n\r\n{}'.format(
            '-----------START-----------',
            (req.method or "") + ' ' + (req.url or ""),
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ))
        return requests.Session().send(req).json()

    def validateCUIT(self: Self, cuit: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCuit.aspx/GetDatosCOmpletosxCuit', '{\'dato\': \'' + cuit + '\'}')
    
    def validateDNI(self: Self, DNI: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioDocumento.aspx/getDatosxDenominacion', '{\'dato\': \'' + DNI + '\', \'tipo\': \'E\'}')
    
    def validateDistrict(self: Self, province: str, district: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetPartidos', '{\'dato\': \'' + district + '\', \'prov\': \'' + province + '\'}')

    def validateCounty(self: Self, province: str, district: str, county: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetLocalidades', '{\'dato\': \'' + county + '\', \'prov\': \'' + province + '\', \'part\': \'' + district + '\'}')
    
    def validateStreet(self: Self, province: str, district: str, county: str, street: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetCalles', '{\'dato\': \'' + street + '\', \'prov\': \'' + province + '\', \'part\': \'' + district + '\', \'localidad\': \'' + county + '\'}')
    
    def validateCPA(self: Self, province: str, district: str, county: str, street: str, number: str):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/getCPA', '{\'prov\': \'' + province + '\', \'part\': \'' + district + '\', \'localidad\': \'' + county + '\', \'calle\': \'' + street + '\', \'numero\': \'' + number + '\'}')
    
    def getStreetHelper(self: Self, province: str, street = str, district: str | None = None, county: str | None = None):
        return self._createRequest('https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetCallesHelper', '{' + f'\'prov\': \'{province}\', \'part\': \'{(district or "")}\', \'localidad\': \'{(county or "")}\', \'calle\': \'{street}\'' + '}')
