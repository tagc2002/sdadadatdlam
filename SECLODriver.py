#selenium webdriver-manager python_dotenv
from enum import Enum
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
from SECLOExceptions import UnauthorizedAccessException
from SECLOExceptions import UnknownReportedException
from SECLOExceptions import RecNotAccessibleException
from SECLOExceptions import InvalidCaseStateException
from SECLOExceptions import ValidationException
from SECLOExceptions import InvalidParameterException

from datetime import datetime
from typing import Self
import os

import logging
logger = logging.getLogger(__name__)

portalVersionSupported = '8.4.10.0'

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

    def __init__(self, credentials: SECLOLoginCredentials, recid: int):
        '''
        Creates a new chrome instance and authorizes login.
        
        Parameters:
            credentials (SECLOLoginCredentials): Wrapper object containing login info.
        Returns:
            SECLOAccessor: Instance of chrome webdriver already logged in and ready for operations
        '''

        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-logging'])
        #chrome_options.add_argument('headless')
        chrome_options.add_experimental_option("detach", True)
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
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnAceptar'))).click()
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

    def __errorHandling(self):
        '''
        Function to handle redirects to /Error.aspx page.
        There's not much to be done other than display some boilerplate error message.
        But if its an auth problem the caller can choose to try again, so we inform this using an exception.
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

    def _loadRec(self: Self):
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Busqueda_btnBuscar')))
        self.driver.execute_script("arguments[0].value = "+ str(self.recid)+ ";", self.driver.find_element(By.NAME, "ctl00$Top$hdnReclamoId"))
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.NAME, 'ctl00$Busqueda$txtNro'))).send_keys(Keys.ENTER)

class SECLONotification(Enum):
    TELEGRAM = 'T'
    AFIP = 'A'
    PERSONAL = 'P'
    DONOTSEND = 'N'
    ELECTRONIC = 'E'
    CEDULE = 'C'

    def NotificationShortToEnum(notif: str):
        if (notif == 'Tel'):
            return SECLONotification.TELEGRAM
        if (notif == 'Per'):
            return SECLONotification.PERSONAL        
        if (notif == 'Afip'):
            return SECLONotification.AFIP
        if ('Electr' in notif):
            return SECLONotification.ELECTRONIC
        if ('No env' in notif):
            return SECLONotification.ELECTRONIC
        if (notif == 'Ced'):
            return SECLONotification.CEDULE

class CitationResult:
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
                self.amount = rowItem.find_elements(By.TAG_NAME, 'td')[4].text.lstrip()
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
            if (self.amount is str):
                return f'person: {self.person}\t enabled: {self.enabled}\t agreement: True\t amount: {self.amount}\t {"absent\t " if self.absent else ""}{"Notify (" + self.citation + ")" if self.notify else "Don't notify"}'
            return f'person: {self.person}\t enabled: {self.enabled}\t agreement: False\t {"absent\t " if self.absent else ""}{"Notify (" + self.citation + ")" if self.notify else "Don't notify"}'
        else: 
            return f'person: {self.person}\t {"absent\t " if self.absent else ""}{"Notify (" + self.citation + ")" if self.notify else "Don't notify"}'
    
    def __hash__(self):
        return hash(self.person, self.amount)
    
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
                if (isinstance(amount, None)):
                    raise InvalidElementStateException("An agreement must have a specified amount")
                elif (amount <= 0):
                    raise InvalidElementStateException("Amount must be positive.")
                else:
                    self.amount = f'{amount:.2f}'
            else:
                if (not isinstance(amount, None)):
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
    def __init__(self, credentials: SECLOLoginCredentials, recid: int, date: datetime):
        super().__init__(credentials, recid)
        logger.debug(f'Created SECLOCitation with recid {str(recid)}')
        self.date = date

    def __loadCitationResultScreen(self: Self) -> None:
        try:
            logger.debug(f'Accessing citation result window')
            self.driver.find_element(By.ID, 'ctl00_btnAudiencia').click()
            self._loadRec()
        except TimeoutException:
            logger.error(f'Timeout accessing SECLO systems. Check connection.')
        except Exception as e:
            logger.error(f'An unknown error has occurred.\n{e}')
        try:
            if ('Registrar Resultado Audiencia' not in self.driver.find_element(By.ID, 'ctl00_Center_tb').find_elements(By.CLASS_NAME, 'appBoxMenuTitle')[1].text):
                raise RecNotAccessibleException
        except Exception as e:
            logger.critical(f'Could not access result form for rec {self.recid}. Maybe its closed.')
            raise RecNotAccessibleException
        else: 
            if (self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos').get_attribute('disabled')):
                logger.debug('Claim object comb selector is disabled. This is good.')
                self.multiple = False
            else:
                logger.warning(f'Attempting to close a partial conciliation. This feature has not been implemented yet. Use this case to code it: {self.recid}')
                logger.debug(self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos').get_attribute('disabled'))
                self.multiple = True
                self.combSelectorLength = len(Select(self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos')).options)
                self.combSelectorIndex = 0

    # Gets the current list of employees and employers registered in this claim
    # Modify this list with the results and new notification if needed and send it to setItems 
    def getItems(self: Self) -> set[CitationResult]:
        logger.debug('Performing Citation getItems')
        self.__loadCitationResultScreen()
        self.fields = []
        try:
            table = self.driver.find_element(By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')
            for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
                self.fields.append(CitationResult(row, True))
                self.fields.append(CitationResult(row, False))
            self.fields = set(self.fields)
            logger.debug(f'Found the following employees in this citation: {self.fields}')
            return self.fields
        except Exception as e:
            logger.error(f'Something happenned loading the result fields.\n{e}')
            raise InvalidCaseStateException

    def __rowPopulatedCheck(self: Self, row: WebElement) -> bool:
        return (not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked") 
                and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked"))

    # Receives a list of results per employee and presentation date, and sets the first form accordingly
    # Also advances to the second form, so that you can call for a new citation or close the case
    def setItems(self: Self, items: set[CitationResult]) -> Self:
        logger.debug('Performing Citation getItems')
        self.__loadCitationResultScreen()
        self.items = items

        if self.multiple:
            if self.combSelectorIndex == self.combSelectorLength:
                return self.__advanceResultForm()
            else:
                Select(self.driver.find_element(By.ID, 'ctl00_Center_cmbObjetos')).select_by_index(self.combSelectorIndex)
                self.combSelectorIndex += 1             
        try:
            for entry in set(items):
                if not entry.isEmployee():
                    continue
                loop = True
                while loop:
                    loop = False
                    logger.debug('Getting table contents')
                    table = self.driver.find_element(By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')
                    for i, row in enumerate(table.find_elements(By.CLASS_NAME, 'grdRowStyle')):
                        if (CitationResult(row) == entry 
                            and self.__rowPopulatedCheck(row)
                            and entry.enabled and CitationResult(row).enabled
                        ):
                            logger.debug(f'Row {i} matches entry {entry} and is unselected, applying...')
                            logger.debug(f'({row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked")} {row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked")})')
                            if (entry.amount is str):
                                #set agreement
                                logger.debug(f'Agreement for {entry}')
                                row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'label').click()
                                row.find_elements(By.TAG_NAME, 'td')[4].find_element(By.TAG_NAME, 'input').send_keys(entry.amount)
                                loop = True
                                break
                            else:
                                #set non-agreement
                                logger.debug(f'Non-agreement for {entry}')
                                row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').click()
                                loop = True
                                break
        except Exception:
            self.__errorHandling()
        for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
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
            del self.error
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
    
    def createNewCitation(self: Self, date: datetime) -> Self:    
        absentCitation = False
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
        
        #TODO validate citation result
        return self

    def closeCase(self: Self) -> Self:
        self.driver.find_element(By.ID, 'ctl00_Center_btnGrabarTotal').click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        alert = self.driver.switch_to.alert.accept()
        if (self.multiple and self.combSelectorIndex < self.combSelectorLength):
            return self.setItems(self.items).closeCase()
        else:
            return self

class SECLOFileType(Enum):
    PODER = ('18', False)
    DNI = ('20', False)
    OTHER = ('21', True)
    CREDENTIAL = ('33', False)
    AUTH = ('34', False)
    SIGNED = ('36', False)

class SECLOFileManager(SECLOAccessor):
    def __init__(self: Self, credentials: SECLOLoginCredentials, recid: int):
        super().__init__(credentials, recid)
        self.__getFiles()

    ## populates internal object storage with the current files in rec
    ## idc about congruency, this is a throwaway object that expires quickly
    def __getFiles(self: Self):
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
        if index >= len(self.fileList) or index < 0:
            raise IndexError("Requesting a file beyond bounds")
        self.getFiles()
        logger.debug("Downloading file")
        download = self.driver.find_element(By.ID, 'grdDocumentos').find_elements(By.CLASS_NAME, 'grdRowStyle')[index].find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input')
        logger.info(download.get_attribute("title"))
        download.click()

    def uploadFile(self: Self, file: str, filetype: SECLOFileType, description: str | None = None):
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
        return
    
    def uploadRecord(self: Self, file: str, agreement: bool):
        self.driver.get('https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx')        
        self._loadRec()
        recNumber = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'ctl00_Busqueda_txtCReclamo'))).text.strip()
        
        WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_btnActa'))).click()
        loadNextPage = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_btnBuscar')))
        if agreement:
            self.driver.find_element(By.ID, 'ctl00_Center_radTipo_0').click()
        else:
            self.driver.find_element(By.ID, 'ctl00_Center_radTipo_1').click()
        loadNextPage.click()
        table = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_grdReclamos')))
        try:
            list = table.find_elements(By.ID, 'grdRowStyle')
        except NoSuchElementException:
            raise InvalidElementStateException("There are no elements available to upload records here. That sucks, man.")
        
        found = False
        for row in list:
            if row.find_elements(By.TAG_NAME, 'td')[0].text.strip() == recNumber:
                #TODO verify if record has already been uploaded
                #I need the site to have a pending case to upload, so later
                row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'input').send_keys(file)
                found = True
                break
        
        if not found:
            raise InvalidElementStateException("Given claim does not have record uploading enabled right now.")
        self.driver.find_element(By.ID, 'ctl00_Center_btnGenerar').click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        return

    ## receives a date in a weird ugly format like 30/dic./2024
    ## and returns a proper datetime object for it
    ## my god i hate this
    def __shitDateToDatetime(self: Self, date: str) -> datetime:
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