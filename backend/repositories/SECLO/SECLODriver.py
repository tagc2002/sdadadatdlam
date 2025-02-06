#selenium webdriver-manager python_dotenv
from enum import Enum
from decimal import Decimal
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import InvalidElementStateException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from backend.repositories.SECLO.SECLOExceptions import UnauthorizedAccessException
from backend.repositories.SECLO.SECLOExceptions import UnknownReportedException
from backend.repositories.SECLO.SECLOExceptions import RecNotAccessibleException
from backend.repositories.SECLO.SECLOExceptions import InvalidCaseStateException
from backend.repositories.SECLO.SECLOExceptions import ValidationException
from backend.repositories.SECLO.SECLOExceptions import InvalidParameterException
from backend.repositories.SECLO.SECLOProgressReporting import ProgressReport

from datetime import datetime
from typing import List, Self
import os
from dotenv import load_dotenv

load_dotenv()

import logging
logger = logging.getLogger(__name__)

logging.getLogger('selenium').setLevel(logging.CRITICAL)

portalVersionSupported = '8.4.11.0'

DEBUGMODE = True
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
    '''

    def __init__(self, credentials: SECLOLoginCredentials, recid: int | None = None, progressReport: ProgressReport | None = ProgressReport()):
        '''
        Creates a new chrome instance and authorizes login.
        
        Parameters:
            credentials (SECLOLoginCredentials): Wrapper object containing login info.
        Returns:
            SECLOAccessor: Instance of chrome webdriver already logged in and ready for operations
        '''

        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-logging'])
        if os.getenv('HEADLESS', 'TRUE') == 'TRUE':
            chrome_options.add_argument('headless')
        else:
            logger.info("Headless flag set true")
        if os.getenv('DETATCH', 'FALSE') == 'TRUE':
            chrome_options.add_experimental_option("detach", True)
            logger.info("Detatch flag set true")
        
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": os.getcwd().join("/temp")
        })

        logger.debug('Creating chrome webdriver service manager instance')
        chrome_service = ChromeService(executable_path=ChromeDriverManager().install())
        #chrome_service.creation_flags = CREATE_NO_WINDOW

        logger.debug('instantiating chrome driver')
        self.driver = webdriver.Chrome(service = chrome_service, options = chrome_options)
        logger.debug('Chrome loaded successfully')

        logger.debug('Getting login page.')
        self.driver.get(f'https://{credentials.user}:{credentials.password}@login-int.trabajo.gob.ar/adfs/ls/wia' + \
            '?wa=wsignin1.0' + \
            '&wtrealm=https%3a%2f%2fconciliadores.trabajo.gob.ar%2f' + \
            '&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f' + \
            '&whr=https%3a%2f%2flogin-int.trabajo.gob.ar%2fadfs%2fservices%2ftrust'
        )
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnAceptar'))).click()
        except (TimeoutException, NoSuchElementException):
            if 'adfs' in self.driver.current_url:
                raise UnauthorizedAccessException("Password is wrong or server entered inactive hours")
        logger.debug('Logged in.')
        
        try:
            WebDriverWait(self.driver,5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ColCerrar'))).click()
            logger.debug('Closed notification panel.')
        except TimeoutException as e:
            logger.debug('Notification popup not found')

        logger.info(self.driver.find_element(By.ID, "ctl00_lblConciliador").text)
        self.portalVersion = self.driver.find_element(By.ID, "ctl00_LblAppVersion").text.split()[1]

        if (self.portalVersion != portalVersionSupported):
            logger.warning(f'Current portal version is {self.portalVersion}, but driver supports up to {portalVersionSupported}. Some features might be unexpectedly broken.')
        else: 
            logger.debug(self.portalVersion)

        self.recid = recid
        self.progress = progressReport

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
                    logger.error('SECLO Authorization error. Try initiating the request again, the token probably expired.')
                    raise UnauthorizedAccessException
                else:
                    logger.error('Unknown SECLO server error. Try initiating the request again.')
                    raise UnknownReportedException
        except NoSuchElementException as e:
            logger.warning('Unknown error, most likely local. idk, man.')

    def _loadRec(self: Self) -> None:
        '''
        Receives an instance of a case searchbox and populates the hiddenRecID field to access the case.
        This method usually does not fail. Searching normally has failed a few times before.
        God I hate this shit site. 
        '''
        if self.recid == None or self.recid == 0:
            raise InvalidParameterException()
        logger.debug(f'Loading recID{self.recid}')
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
        self.driver.execute_script("arguments[0].value = "+ str(self.recid)+ ";", self.driver.find_element(By.NAME, "ctl00$Top$hdnReclamoId"))
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.NAME, 'ctl00$Busqueda$txtNro'))).send_keys(Keys.ENTER)

    def setRecIDfromGDEID(self: Self, gdeID: str):
        '''
        Sets the current RecID to the corresponding key for the given gdeID.

        Parameters:
            gdeID (str): The given gdeID to find a case. eg: "EX-2020-00000000-bullshit"
        '''

        self.progress.setSteps(1)
        self.progress.setProgress(0,"Setting recID")
        logger.debug(f'Setting recID from gdeID {gdeID}')
        self.driver.get('https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx')
        gdeYear = gdeID.split('-')[1]
        gdeFile = gdeID.split('-')[2]
        findButton = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
        self.driver.find_element(By.ID, 'ctl00_Busqueda_txtNro').send_keys(gdeFile)
        self.driver.find_element(By.ID, 'ctl00_Busqueda_txtAnio').send_keys(Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.ARROW_RIGHT+Keys.BACKSPACE+Keys.BACKSPACE+Keys.BACKSPACE+Keys.BACKSPACE+gdeYear)
        findButton.click()
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_grdNotificaciones')))
        recID = self.driver.find_element(By.ID, 'ctl00_Top_hdnReclamoId').get_attribute('value')
        self.recid = recID
        self.progress.setCompletion("Done")
        logger.info(f'recID found, set to {self.recid}')

class SECLONotification(Enum):
    TELEGRAM = 'T'
    AFIP = 'A'
    PERSONAL = 'P'
    DONOTSEND = 'N'
    ELECTRONIC = 'E'
    CEDULE = 'C'

    def NotificationShortToEnum(notif: str):
        '''
        Parses a notification ID from the website into a enum object.
        '''
        if (notif == 'Tel'):
            return SECLONotification.TELEGRAM
        if (notif == 'Per'):
            return SECLONotification.PERSONAL        
        if (notif == 'Afip'):
            return SECLONotification.AFIP
        if ('Electr' in notif):
            return SECLONotification.ELECTRONIC
        if ('No env' in notif):
            return SECLONotification.DONOTSEND
        if (notif == 'Ced'):
            return SECLONotification.CEDULE

class CitationResult:
    '''
    A class designed to hold a citation result to be passed to and from the function caller.
    Holds name, amount, agreement, notification info and whether it's an employee or employer.
    Implements fancy __eq__ to allow duplicate detection.
    '''
    def __init__(self, rowItem: WebElement, isEmployee: bool = True):
            if (isEmployee):
                try:
                    if (rowItem.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].get_attribute("disabled") is None):
                        self.enabled = True
                    else:
                        self.enabled = False
                except NoSuchElementException as e:
                    logger.warning('could not access properties for agreement selector switch.')
                    self.enabled = True
                self.amount = rowItem.find_elements(By.XPATH, './*')[4].find_element(By.TAG_NAME, 'input').text.lstrip()
                logger.debug(f'Amount string "{self.amount}"')
                if len(self.amount) == 0:
                    self.amount = None
                self.person = rowItem.find_elements(By.TAG_NAME, 'td')[0].text
            else:
                self.person = rowItem.find_elements(By.TAG_NAME, 'td')[1].text
            self.notify = False
            self.absent = False
            self.notificationMethod = SECLONotification.TELEGRAM
            logger.debug(f'Created instance of CitationResult with {str(self)}')

    def __eq__(self, other):
        if not isinstance(other, CitationResult):
            return NotImplemented
        return self.person == other.person and (hasattr(self, 'amount') == hasattr(other, 'amount'))
    
    def __str__(self):
        if hasattr(self, 'amount'):
            if (self.amount is not None):
                return f'person: {self.person}\t enabled: {self.enabled}\t agreement: True\t amount: {self.amount}\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
            return f'person: {self.person}\t enabled: {self.enabled}\t agreement: False\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
        else: 
            return f'person: {self.person}\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
    
    def __hash__(self):
        if hasattr(self, 'amount'):
            return hash((self.person, self.amount))
        else:
            return hash(self.person)
    
    def getPerson(self: Self) -> str:
        return self.person
    
    def isEmployee(self: Self) -> bool:
        return hasattr(self, 'amount')
    
    def getResult(self: Self) -> tuple[bool, float | None]:
        if hasattr(self, 'amount'):
            return (isinstance(self.amount, str), self.amount)
        else:
            raise InvalidElementStateException("Can't get result for an employer")
    
    def setResult(self: Self, agreement: bool, amount: float | None = None):
        if self.isEmployee():
            if agreement:
                if amount is None:
                    raise InvalidElementStateException("An agreement must have a specified amount")
                elif amount <= 0:
                    raise InvalidElementStateException("Amount must be positive.")
                else:
                    self.amount = f'{amount:.2f}'
            else:
                if amount is not None:
                    raise InvalidElementStateException("Can't give an amount for a non-agreement result")
                else:
                    self.amount = None
        else:
            raise InvalidElementStateException("Can only set result for employee.")
        
    def setNotification(self: Self, notify: bool, absent: bool = False, method: SECLONotification | None = None):
        if notify:
            self.notify = True
            self.absent = absent
            if (isinstance(method, SECLONotification)):
                self.notificationMethod = method
            else:
                raise InvalidElementStateException("Must provide a notification method to notify.")
        else:
            self.notify = False
            self.absent = absent

class SECLOCitation(SECLOAccessor):
    '''
    A browser driver class to register citation results on the SECLO site. 
    Used for creating a new citation or closing a case with or without agreement.
    Most methods return self for easy chaining.
    eg. citation= SECLOCitation().setRecIDfromGDEID().getItems()
        citation.closeCase()
        citation.createNewCitation()
    '''
    def __init__(self, credentials: SECLOLoginCredentials, recid: int | None = None, date: datetime = datetime.now(), progress: ProgressReport | None = ProgressReport()):
        '''
        Creates the instance.
        Parameters:
            credentials(SECLOLoginCredentials): The credential instance to authorize the requests.
            recid (int | None): The recID to set for this instance. Can be set to None if it will be later set by gdeID, but it cant be none when actually loading.
            date (datetime): The presentation date to set for the result form. Current date by default.
        '''
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

    def reopenCase(self: Self):
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
            self.driver.find_element(By.ID, 'ctl00_Busqueda_grdReclamos')
        except NoSuchElementException:
            pass
        else:
            raise InvalidCaseStateException("Case not found, probably its still open")
        reopenButton = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnReabrir')))
        try:
            error = self.driver.find_element(By.ID, 'ctl00_Center_lblmensaje')
        except NoSuchElementException:
            pass
        else:
            raise InvalidCaseStateException(error)
        reopenButton.click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        alert = self.driver.switch_to.alert.accept()
        self.progress.setCompletion("Done reopening")

    def getItems(self: Self, items: List[CitationResult]):
        '''
        Gets the current list of employees and employers registered in this claim.
        Modify this list with the results and new notification if needed and send it to setItems.
        Parameters:
            items (set[CitationResult]): Empty list, which will be populated with involved entities. This is done to allow returning it from a thread from a thread Must set agreement info on workers, and notification info on all if new citation.
        '''
        self.progress.setSteps(2)
        logger.info('Performing Citation getItems')
        self.progress.setProgress(0, "Loading case")
        self.__loadCitationResultScreen()
        self.fields = []
        self.fieldsLen = 0
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
            for item in self.fields:
                items.append(item)
        except Exception as e:
            logger.error(f'Something happenned loading the result fields.\n{e}')
            raise InvalidCaseStateException

    def __rowPopulatedCheck(self: Self, row: WebElement) -> bool:
        return (not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked") 
                and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked"))

    def __setItems(self: Self, ignoreMultipleComb) -> Self:
        logger.info('Performing Citation getItems')
        self.__loadCitationResultScreen()
        
        if self.multiple:
            if self.combSelectorIndex == self.combSelectorLength:
                return self.__advanceResultForm()
            else:
                Select(WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_cmbObjetos')))).select_by_index(self.combSelectorIndex)
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
                if row.find_elements(By.TAG_NAME, 'td')[0] in entry.getPerson() and row.find_elements(By.TAG_NAME, 'td')[1] in entry.getPerson():
                    if (entry.absent):
                        row.find_elements(By.TAG_NAME, 'td')[2].find_element(By.TAG_NAME, 'input').click()
                    if (entry.notify):
                        if absentCitation:
                            row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input').click()
                        Select(row.find_elements(By.TAG_NAME, 'td')[4 if absentCitation else 2].find_element(By.TAG_NAME, 'select')).select_by_value(entry.notificationMethod.value)
                    break
        for row in self.driver.find_element(By.ID, 'ctl00_Center_grdEmpleadores').find_elements(By.CLASS_NAME, 'grdRowStyle'):
            for entry in self.items:
                if row.find_elements(By.TAG_NAME, 'td')[0] in entry.getPerson():
                    if (entry.absent):
                        row.find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').click()
                    if (entry.notify):
                        if absentCitation:
                            row.find_elements(By.TAG_NAME, 'td')[2].find_element(By.TAG_NAME, 'input').click()
                        Select(row.find_elements(By.TAG_NAME, 'td')[3 if absentCitation else 1].find_element(By.TAG_NAME, 'select')).select_by_value(entry.notificationMethod.value)
       
        self.driver.find_element(By.ID, 'ctl00_Center_btnGrabar').click()
        self.__validationErrorChecker()
        self.progress.setCompletion("Done new citation request")
        self.driver.quit()
        #TODO validate citation result
        return

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
        self.progress.setCompletion("Done closing claim")
        self.driver.quit()

class SECLOFileType(Enum):
    PODER = ('18', False)
    DNI = ('20', False)
    OTHER = ('21', True)
    CREDENTIAL = ('33', False)
    AUTH = ('34', False)
    SIGNED = ('36', False)

class SECLOFileManager(SECLOAccessor):
    '''A class to handle file management, including querying and downloading already present files, uploading new ones, or uploading records.'''
    def __init__(self: Self, credentials: SECLOLoginCredentials, recid: int):
        super().__init__(credentials, recid)
        self.__getFiles()

    def __getFiles(self: Self):
        '''
        populates internal object storage with the current files in rec
        idc about congruency, this is a throwaway object that expires quickly
        '''
        self.driver.get(f'https://conciliadores.trabajo.gob.ar/Documentacion_Adjunta.aspx?RecId={self.recid}')
        files = []
        for row in self.driver.find_element(By.ID, 'grdDocumentos').find_elements(By.CLASS_NAME, 'grdRowStyle'):
            files.append((
                row.find_elements(By.TAG_NAME, 'td')[0].text,
                row.find_elements(By.TAG_NAME, 'td')[1].text,
                self.__shitDateToDatetime(
                    row.find_elements(By.TAG_NAME, 'td')[2].text
                )
            ))
        self.fileList = files

    def getFiles(self: Self):
        '''
        Gets a list of all the registered files currently uploaded to this rec.
        Returns: 
            Tuple[str, str, datetime]: (type, description, date)
        '''
        return self.fileList[:]
    
    def getFile(self: Self, index: int):
        '''
        Request a given file from the list of uploaded file.
        Parameters:
            index (int): The index of the requested file
        Returns:
            Nothing currently, but hopefully later a handle to the downloaded file.
        '''
        if index >= len(self.fileList) or index < 0:
            raise IndexError("Requesting a file beyond bounds")
        self.getFiles()
        logger.debug("Downloading file")
        download = self.driver.find_element(By.ID, 'grdDocumentos').find_elements(By.CLASS_NAME, 'grdRowStyle')[index].find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input')
        logger.info(download.get_attribute("title"))
        download.click()

    def uploadFile(self: Self, file: str, filetype: SECLOFileType, description: str | None = None):
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
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'Button1'))).click()
        self.__getFiles()
    
    def uploadRecord(self: Self, file: str, agreement: bool):
        '''
        Uploads a record to an already closed case.
        Parameters:
            file (str): Path to the desired record to upload.
            agreement (bool): Whether its an agreement or not, because the way of uploading them is different for some godforsaken reason. 
        '''
        self.driver.get(f'https://conciliadores.trabajo.gob.ar/Conciliador_Reclamo.aspx?RecId={self.recid}')        
        recNumber = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'rcNroExpediente'))).text.strip()
        logger.info(recNumber)
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
            if row.find_elements(By.TAG_NAME, 'td')[0].text.strip() == recNumber:
                #TODO verify if record has already been uploaded
                #I need the site to have a pending case to upload, so later
                row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input').send_keys(file)
                found = True
                break  
        else:
            raise InvalidElementStateException("Given claim does not have record uploading enabled right now.")
        self.driver.find_element(By.ID, 'ctl00_Center_btnGenerar').click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_grdReclamos')))
        return


    def __shitDateToDatetime(self: Self, date: str) -> datetime:
        '''
        receives a date in a weird ugly format like 30/dic./2024
        and returns a proper datetime object for it
        my god i hate this      
        '''
        day = int(date.split('/')[0])
        month = date.split('/')[1]
        year = int(date.split('/')[2])
        if 'ene' in month:
            month = 1
        elif 'feb' in month:
            month = 2
        elif 'mar' in month:
            month = 3
        elif 'abr' in month:
            month = 4
        elif 'may' in month:
            month = 5
        elif 'jun' in month:
            month = 6
        elif 'jul' in month:
            month = 7
        elif 'ago' in month:
            month = 8
        elif 'sep' in month:
            month = 9
        elif 'oct' in month:
            month = 10        
        elif 'nov' in month:
            month = 11
        elif 'dic' in month:
            month = 12
        return datetime(day = day, month = month, year = year)

class SECLORecData(SECLOAccessor):
    def getNotificationData(self: Self):
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
    
    def getClaimData(self: Self):
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkModificacion'))).click()
        self._loadRec()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ucReclamo_txtFecha')))
        seclodbOK = True
        #CLAIM
        claimData = SECLOClaimData(
            recid = self.recid,
            legalStuff = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_txtComentario').get_attribute('value'),
            initWorker = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_optReclamante_0').get_attribute('checked')
        )

        for row in self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_chkObjetoReclamo').find_elements(By.TAG_NAME, 'td'):
            if row.find_element(By.TAG_NAME, 'input').get_attribute('checked'):
                claimData.addClaimObject(row.find_element(By.TAG_NAME, 'label').text)
        
        #EMPLOYEES
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstTrabajadores').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstTrabajadores')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()
            
            cuil = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl00_cuit_txtC')))
            name = f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNombre_txt').get_attribute('value')}',
            if len(cuil.text) > 0 and seclodbOK:
                cuil.click()
                cuil.send_keys(Keys.TAB)
                WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value')) > 0)
                if 'null null' not in self.driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value'):
                    name = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value')
                else:
                    seclodbOK = False
            employee = SECLOEmployeeData(
                name = name,
                DNI = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS').get_attribute('value'),
                CUIL = cuil.get_attribute('value'),
                validated = seclodbOK
            )
            employee.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtProvincia').get_attribute('value'),
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtPartido').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtLocalidad').get_attribute('value'),
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtCalle').get_attribute('value'),
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtDepart').get_attribute('value'),
                    CPA=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )
            employee.addBirthDate(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecNacimiento_txt').get_attribute('value'))
            employee.addClaimAmount(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtImporte_txt').get_attribute('value'))
            employee.addEndDate(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecEgreso_txt').get_attribute('value'))
            employee.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtEmail_txt').get_attribute('value'))
            employee.addMobilePhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCodArea_Numerico').get_attribute('value'), self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCel_Numerico').get_attribute('value'))
            employee.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtTelefono_txt').get_attribute('value'))
            employee.addStartDate(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtFecIngreso_txt').get_attribute('value'))
            employee.addType(CCT = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtConvenioNum_txt').get_attribute('value'), category = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtCategoria_txt').get_attribute('value'))
            employee.addWage(self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtRemuneracion_txt').get_attribute('value'))
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
            employer = SECLOEmployerData(
                name=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtRS').get_attribute('value'),
                DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtNroDocumento_txt').get_attribute('value'),
                CUIL=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtC').get_attribute('value'),
                validated = seclodbOK
            )
            employer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtProvincia').get_attribute('value'),
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPartido').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtLocalidad').get_attribute('value'),
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCalle').get_attribute('value'),
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtDepart').get_attribute('value'),
                    CPA=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )
            employer.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtTelefono_txt').get_attribute('value'))
            for item in self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cmbTipoSociedad_cmb').find_elements(By.TAG_NAME, 'option'):
                if item.get_attribute('selected'):
                    employer.addPersonType(item.text)
            employer.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtTelefono_txt').get_attribute('value'))
            claimData.addEmployer(employer)
            #WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_btnAgregar'))).click()
            i += 1
        
        #LAWYERS
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstReprentantes').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            list = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_lstReprentantes')))
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(list.find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a'))).click()

            email = self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtEmail_txt').get_attribute('value').strip()
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

            lawyer = SECLOLawyerData(
                name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text} {self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtApellido_lbl').text}',
                DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNroDocumento_lbl').text,
                validated = seclodbOK
            )
            lawyer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtProvincia').get_attribute('value'),
                    district=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPartido').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtLocalidad').get_attribute('value'),
                    street=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtCalle').get_attribute('value'),
                    number=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtNumero').get_attribute('value'),
                    floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPiso').get_attribute('value'),
                    apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtDepart').get_attribute('value'),
                    CPA=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtCPA').get_attribute('value'),
                    bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtAdicional').get_attribute('value')
                )
            )

            for row in self.driver.find_element(By.ID, 'ctl00_Center_ctl02_lstAsignados').find_elements(By.TAG_NAME, 'td'):
                if row.find_element(By.TAG_NAME, 'input').get_attribute('checked'):
                    name = row.text.replace(',', '')
                    lawyer.addRepresented(
                        isEmployee=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_chkRepresentantes_0').get_attribute('checked'), 
                        name=name
                    )
            lawyer.addPhone(phone)
            lawyer.addMobilePhone(prefix=mobileprefix, phone=mobilephone)
            lawyer.addMail(email)
            lawyer.addTF(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtTomo_txt').get_attribute('value'), self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtFolio_txt').get_attribute('value'))
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
                other = SECLOOtherData(
                    name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNombre_txt').get_attribute('value')}',
                    DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNroDocumento_txt').get_attribute('value'),
                )
                other.addAddress(
                    SECLOAddressData(
                        province=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtProvincia').get_attribute('value'),
                        district=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtPartido').get_attribute('value'),
                        county=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtLocalidad').get_attribute('value'),
                        street=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtCalle').get_attribute('value'),
                        number=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtNumero').get_attribute('value'),
                        floor=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtPiso').get_attribute('value'),
                        apt=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtDepart').get_attribute('value'),
                        CPA=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtCPA').get_attribute('value'),
                        bonusData=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtAdicional').get_attribute('value')
                    )
                )
                other.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtEmail_txt').get_attribute('value'))
                other.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtTelefono_txt').get_attribute('value'))
                other.addMobilePhone(prefix=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtCodArea_Numerico').get_attribute('value'), phone=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtCel_Numerico').get_attribute('value'))
                claimData.addOther(other)
                i += 1

        #END
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lnkFinalizar'))).click()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnAceptarRec'))).click()
        #WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnSi'))).click()
        #WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        #alert = self.driver.switch_to.alert.accept()
        return claimData

class SECLOAddressData():
    def __init__(self: Self, province: str, district: str, county: str, street: str, number: str | None = None, floor: str | None = None, apt: str | None = None, CPA: str | None = None, bonusData: str | None = None):
        self.province = province
        self.district = district
        self.county = county
        self.street = street
        self.number = number
        self.floor = floor
        self.apt = apt
        self.CPA = CPA
        self.bonusData = bonusData
    def __str__(self: Self):
        return f'{self.street} {self.number}, {self.floor} {self.apt}, {self.county}, {self.district}, {self.province}, {self.CPA} {self.bonusData}'
 
class SECLOCommonData():
    def __init__(self: Self, name: str, DNI: int | None = None, CUIL: str | None = None, validated: bool = False):
        self.name = name
        self.DNI = DNI
        self.CUIL = CUIL
        self.address = []
        self.mail = ''
        self.phone = ''
        self.mobilePhone = ''
        self.validated = validated
    
    def addAddress(self: Self, address: SECLOAddressData):
        self.address.append(address)
    def addMail(self: Self, mail: str | None = None):
        self.mail = mail
    def addPhone(self: Self, phone: str | None):
        self.phone = phone
    def addMobilePhone(self: Self, prefix: str, phone: str):
        self.mobilePhone = (prefix, phone)
    def __str__(self: Self):
        base = f'Name: {self.name}\nDNI: {self.DNI}\nCUIT: {self.CUIL}\nvalidated: {self.validated}\nphone: {self.phone} / {self.mobilePhone}\nmail: {self.mail}\naddress:\n'
        for address in self.address:
            base = base + str(address) + '\n'
        return base

class SECLOEmployeeData(SECLOCommonData):
    def addBirthDate(self: Self, date: datetime):
        self.birthDate = date
    def addStartDate(self: Self, date: datetime):
        self.startDate = date
    def addEndDate(self: Self, date: datetime | None):
        self.endDate = date
    def addWage(self: Self, amount: int):
        self.wage = amount
    def addType(self: Self, CCT: int | None = None, category: str | None = None):
        self.CCT = CCT
        self.category = category
    def addClaimAmount(self: Self, amount: int):
        self.claimAmount = amount
    def __str__(self: Self):
        return f'{super().__str__()}Birthdate: {self.birthDate}\nWorkdates: {self.startDate} - {self.endDate}\nwage: {self.wage}\nworktype: {self.category} - {self.CCT}\nclaim: {self.claimAmount}'
    
class SECLOEmployerData(SECLOCommonData):
    def addPersonType(self: Self, personType: str):
        self.personType = personType
    def __str__(self: Self):
        return f'{super().__str__()}Type: {self.personType}'

class SECLOLawyerData(SECLOCommonData):
    def __init__(self: Self, name: str, DNI: int | None = None, CUIL: str | None = None, validated: bool = False):
        super().__init__(name, DNI, CUIL, validated)
        self.represents = []
    def addTF(self: Self, t: int, f: int):
        self.t = t
        self.f = f
    def addRepresented(self: Self, isEmployee: bool, name: str):
        self.represents.append((isEmployee, name))
        pass
    def __str__(self: Self):
        return f'{super().__str__()}T {self.t} F {self.f}\n{self.represents}\n'

class SECLOOtherData(SECLOCommonData):
    pass
    
class SECLOClaimData():
    def __init__(self: Self, recid: int, legalStuff: str, initWorker: bool):
        self.recid = recid
        self.legalStuff = legalStuff
        self.initWorker = initWorker
        self.claims = []
        self.employees = []
        self.employers = []
        self.lawyers = []
        self.others = []

    def addClaimObject(self: Self, claim: str):
        self.claims.append(claim)

    def addEmployee(self: Self, employee: SECLOEmployeeData):
        self.employees.append(employee)
    
    def addEmployer(self: Self, employer: SECLOEmployerData):
        self.employers.append(employer)

    def addLawyer(self: Self, lawyer: SECLOLawyerData):
        self.lawyers.append(lawyer)

    def addOther(self: Self, other: SECLOOtherData):
        self.others.append(other)

    def __str__(self: Self):
        base = f'CLAIM:\n\nrecID {self.recid}\nlegal stuff: {self.legalStuff}\nclaims:\n{self.claims}'
        base = base + '\n\nemployees:\n'
        for employee in self.employees:
            base = base + f'{str(employee)}\n'

        base = base + '\nemployers:\n'
        for employer in self.employers:
            base = base + f'{str(employer)}\n'   

        base = base + '\nlaywers:\n'
        for lawyer in self.lawyers:
            base = base + f'{str(lawyer)}\n' 

        if len(self.others) > 0:
            base = base + '\nothers:\n'
            for other in self.others:
                base = base + f'{str(other)}\n'
        
        return base
    
class SECLOInvoiceParser(SECLOAccessor):
    def listInvoices(self: Self):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkConsultaLiquidacion'))).click()
        invoices = []
        for option in WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_cmbLiquidaciones'))).find_elements(By.TAG_NAME, 'option'):
            invoices.append({'id': int(option.get_attribute('value')), 'date':datetime.strptime(option.text.split()[0], "%d/%m/%Y")})
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
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_btnAgenda'))).click()

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_chkSusp'))).click()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_chkReal'))).click()

        #Loop through weeks
        IDs = []
        for i in range(0, 20):
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
        
        calendarCitations = []
        for item in IDs:
            self.driver.get(f'https://conciliadores.trabajo.gob.ar/Conciliador_Audiencia.aspx?AudId={item}&esPortal=1')
            gdeIDText = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'rcNroExpediente'))).text
            initDatetimeText = self.driver.find_element(By.ID, 'rcFecha').text
            initDateTimeText = initDatetimeText.split()[0] + ' ' + initDatetimeText.split()[1].split(':')[0] + ':' + initDatetimeText.split()[1].split(':')[1]
            calendarCitations.append(
                {'gdeID': gdeIDText,
                 'citationDate': datetime.strptime(self.driver.find_element(By.ID, 'rcFechaA').text.split('a')[0], r'%d/%m/%Y - %H:%M '),
                 'initDate': datetime.strptime(initDateTimeText, r'%d/%m/%Y %H:%M'),
                 'audID': item
                }), 
        return calendarCitations

class SECLOClaimValidationData(SECLOAccessor):
    def _createRequest(self: Self, endpoint: str, data: str):
        cookies = {}
        cookies['FedAuth'] = self.driver.get_cookie('FedAuth')['value']
        cookies['FedAuth1'] = self.driver.get_cookie('FedAuth1')['value']
        cookies['ASP.NET_SessionId'] = self.driver.get_cookie('ASP.NET_SessionId')['value']
        cookies['TS01503a54'] = self.driver.get_cookie('TS01503a54')['value']
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
            req.method + ' ' + req.url,
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