#selenium webdriver-manager python_dotenv
from enum import Enum
from decimal import Decimal
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

    def __init__(self, credentials: SECLOLoginCredentials, recid: int | None = None):
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
    
    def getClaimData(self: Self):
        WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.ID, 'ctl00_lnkModificacion'))).click()
        self._loadRec()
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ucReclamo_txtFecha')))

        #CLAIM
        logger.info(self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_lblReclamo_GDEID').text)
        logger.info(self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_txtFecha').get_attribute('value'))
        claimData = SECLOClaimData(
            recid = self.recid,
            gdeID = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_lblReclamo_GDEID').text,
            initDate = self.driver.find_element(By.ID, 'ctl00_Center_ucReclamo_txtFecha').get_attribute('value'),
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
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lstTrabajadores'))).find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a').click()
            cuil = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl00_cuit_txtC')))
            if len(cuil.text) > 0:
                cuil.click()
                cuil.send_keys(Keys.TAB)
                WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value')) > 0)
                employee = SECLOEmployeeData(
                    name = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_cuit_txtRS').get_attribute('value'),
                    DNI = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS').get_attribute('value'),
                    CUIL = cuil.get_attribute('value')
                )
            else:
                #TODO use requests library to ensure this shit
                employee = SECLOEmployeeData(
                    name = f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNombre_txt').get_attribute('value')}',
                    DNI = self.driver.find_element(By.ID, 'ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS').get_attribute('value'),
                    CUIL = cuil.get_attribute('value')
                )
            employee.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtProvincia').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtPartido').get_attribute('value'),
                    borough=self.driver.find_element(By.ID, 'ctl00_Center_ctl00_Domicilio_direc_txtLocalidad').get_attribute('value'),
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
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl00_btnAgregar'))).click()
            i += 1

        #EMPLOYERS
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstEmpleadores').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lstEmpleadores'))).find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a').click()
            WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl01_cuit_txtRS')))
            employer = SECLOEmployerData(
                name=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtRS').get_attribute('value'),
                DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_txtNroDocumento_txt').get_attribute('value'),
                CUIL=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_cuit_txtC').get_attribute('value')
            )
            employer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtProvincia').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtPartido').get_attribute('value'),
                    borough=self.driver.find_element(By.ID, 'ctl00_Center_ctl01_Domicilio_direc_txtLocalidad').get_attribute('value'),
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
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl01_btnAgregar'))).click()
            i += 1
        
        #LAWYERS
        listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstReprentantes').find_elements(By.TAG_NAME, 'li'))
        i = 0
        while i < listLen:
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lstReprentantes'))).find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a').click()
            folio = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl02_txtFolio_txt')))
            foliovalue = folio.get_property('value')
            folio.send_keys(Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE)
            folio.send_keys(str(foliovalue))
            folio.send_keys(Keys.TAB)
            WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPartido').get_attribute('value')) > 0)
            lawyer = SECLOLawyerData(
                name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text} {self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtApellido_lbl').text}',
                DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtNroDocumento_lbl').text,
            )
            streetnumber = self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtNumero')
            streetnumbervalue = streetnumber.get_attribute('value')
            streetnumber.send_keys(Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + '0' + Keys.TAB)
            streetnumber.send_keys(Keys.ARROW_RIGHT + Keys.BACKSPACE + str(streetnumbervalue))
            streetnumber.send_keys(Keys.TAB)
            WebDriverWait(self.driver, 5).until(lambda driver: len(driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtCPA').get_attribute('value')) > 0)
            lawyer.addAddress(
                SECLOAddressData(
                    province=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtProvincia').get_attribute('value'),
                    county=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtPartido').get_attribute('value'),
                    borough=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_Domicilio_direc_txtLocalidad').get_attribute('value'),
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
                    name = row.get_attribute('value')
            lawyer.addRepresented(
                isEmployee=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_chkRepresentantes_0').get_attribute('checked'), 
                name=name
            )
            lawyer.addPhone(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtTelefono_txt').get_attribute('value'))
            lawyer.addMobilePhone(prefix=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtCodArea_Numerico').get_attribute('value'), phone=self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtCel_Numerico').get_attribute('value'))
            lawyer.addMail(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtEmail_txt').get_attribute('value'))
            lawyer.addTF(self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtTomo_txt').get_attribute('value'), self.driver.find_element(By.ID, 'ctl00_Center_ctl02_txtFolio_txt').get_attribute('value'))
            claimData.addLawyer(lawyer)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_ctl02_btnAgregar'))).click()
            i += 1       
        
        #OTHERS
        try:
            listLen = len(self.driver.find_element(By.ID, 'ctl00_Center_lstDerechohabientes').find_elements(By.TAG_NAME, 'li'))
        except NoSuchElementException:
            pass
        else:
            i = 0
            while i < listLen:
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'ctl00_Center_lstDerechohabientes'))).find_elements(By.TAG_NAME, 'li')[i].find_element(By.TAG_NAME, 'a').click()
                WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl03_txtNombre_txt')))
                other = SECLOOtherData(
                    name=f'{self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtApellido_txt').get_attribute('value')} {self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNombre_txt').get_attribute('value')}',
                    DNI=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_txtNroDocumento_txt').get_attribute('value'),
                )
                other.addAddress(
                    SECLOAddressData(
                        province=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtProvincia').get_attribute('value'),
                        county=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtPartido').get_attribute('value'),
                        borough=self.driver.find_element(By.ID, 'ctl00_Center_ctl03_Domicilio_direc_txtLocalidad').get_attribute('value'),
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

        return claimData

class SECLOAddressData():
    def __init__(self: Self, province: str, county: str, borough: str, street: str, number: str | None = None, floor: str | None = None, apt: str | None = None, CPA: str | None = None, bonusData: str | None = None):
        self.province = province
        self.county = county
        self.borough = borough
        self.street = street
        self.number = number
        self.floor = floor
        self.apt = apt
        self.CPA = CPA
        self.bonusData = bonusData
        logger.critical(str(self))
    def __str__(self: Self):
        return f'{self.street} {self.number}, {self.floor} {self.apt}, {self.borough}, {self.county}, {self.province}, {self.CPA}\n{self.bonusData}'
 
class SECLOCommonData():
    def __init__(self: Self, name: str, DNI: int | None = None, CUIL: str | None = None):
        self.name = name
        self.DNI = DNI
        self.CUIL = CUIL
        self.address = []
        self.mail = ''
        self.phone = ''
        self.mobilePhone = ''
    
    def addAddress(self: Self, address: SECLOAddressData):
        self.address.append(address)
    def addMail(self: Self, mail: str | None = None):
        self.mail = mail
    def addPhone(self: Self, phone: str | None):
        self.phone = phone
    def addMobilePhone(self: Self, prefix: str, phone: str):
        self.mobilePhone = (prefix, phone)
    def __str__(self: Self):
        base = f'Name: {self.name}\nDNI: {self.DNI}\nCUIT: {self.CUIL}\nphone: {self.phone} / {self.mobilePhone}\nmail: {self.mail}\naddress:\n'
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
        return f'{super().__str__()}\nBirthdate: {self.birthDate}\nWorkdates: {self.startDate} - {self.endDate}\nwage: {self.wage}\nworktype: {self.category} - {self.CCT}\nclaim: {self.claimAmount}'
    
class SECLOEmployerData(SECLOCommonData):
    def addPersonType(self: Self, personType: str):
        self.personType = personType
    def __str__(self: Self):
        return f'{super().__str__()}\nType: {self.personType}'

class SECLOLawyerData(SECLOCommonData):
    def addTF(self: Self, t: int, f: int):
        self.t = t
        self.f = f
    def addRepresented(self: Self, isEmployee: bool, name: str):
        #TODO chech this shit
        pass
    def __str__(self: Self):
        return f'{super().__str__()}\nT {self.t} F {self.f}'

class SECLOOtherData(SECLOCommonData):
    pass
    
class SECLOClaimData():
    def __init__(self: Self, recid: int, gdeID: str, initDate: str, legalStuff: str, initWorker: bool):
        self.recid = recid
        self.gdeID = gdeID
        self.initDate = datetime.strptime(initDate, '%d/%m/%Y'),
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
        base = f'CLAIM:\n\nrecID {self.recid}\nGDE {self.gdeID}\ninit: {str(self.initDate)}\nlegal stuff: {self.legalStuff}\nclaims:\n{self.claims}'
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
