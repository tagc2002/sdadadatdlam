#selenium webdriver-manager python_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
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
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

portalVersionSupported = '8.4.10.0'

def createWebdriver():
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ['enable-logging'])
    #chrome_options.add_argument('headless')
    chrome_options.add_experimental_option("detach", True)
    logger.debug('Creating chrome webdriver manager instance')
    chrome_service = ChromeService(executable_path=ChromeDriverManager().install())
    #chrome_service.creation_flags = CREATE_NO_WINDOW
    logger.debug('instantiating chrome driver')
    driver = webdriver.Chrome(service = chrome_service, options = chrome_options)
    logger.debug('Chrome loaded successfully')
    return driver

class SECLOLoginCredentials:
    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password

class SECLOAccessor:
    def __init__(self, credentials: SECLOLoginCredentials):
        self.driver = createWebdriver()
        token = False
        try:
            logger.debug('Getting login page.')
            self.driver.get(f'https://{credentials.user}:{credentials.password}@login-int.trabajo.gob.ar/adfs/ls/wia'
                '?wa=wsignin1.0' + \
                '&wtrealm=https%3a%2f%2fconciliadores.trabajo.gob.ar%2f' + \
                '&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f' + \
                '&whr=https%3a%2f%2flogin-int.trabajo.gob.ar%2fadfs%2fservices%2ftrust'
            )
            self.driver.find_element(By.ID, "ctl00_Center_btnAceptar").click()
            logger.debug('Logged in.')
        except Exception as e:
            logger.error(f'(Time: {datetime.datetime.now()}): Token aquisition error, {str(e)}')
        
        WebDriverWait(self.driver,1)
        try:
            self.driver.find_element(By.CLASS_NAME, "ColCerrar").click()
            logger.debug('Closed notification panel.')
        except NoSuchElementException as e:
            logger.debug('Notification popup not found')

        token = True
        logger.info(self.driver.find_element(By.ID, "ctl00_lblConciliador").text)
        self.portalVersion = self.driver.find_element(By.ID, "ctl00_LblAppVersion").text

        if (self.portalVersion != portalVersionSupported):
            logger.warning(f'Current portal version is {self.portalVersion}, but driver supports up to {portalVersionSupported}. Some features might be unexpectedly broken.')
        else: 
            logger.debug(self.portalVersion)
    
    def __errorHandling(self):
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

class CitationResult:
    def __init__(self, rowItem: WebElement):
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
            self.employee = rowItem.find_elements(By.TAG_NAME, 'td')[0].text
            logger.debug(f'Created instance of CitationResult with {str(self)}')

    def __eq__(self, other):
        if not isinstance(other, CitationResult):
            return NotImplemented
        return self.employee == other.employee
    
    def __str__(self):
        if (self.amount is str):
            return f'employee: {self.employee}\t enabled: {self.enabled}\t agreement: True\t amount: {self.amount}'
        return f'employee: {self.employee}\t enabled: {self.enabled}\t agreement: False'
    
    def __hash__(self):
        return hash(self.employee)

class SECLOCitation(SECLOAccessor):
    def __init__(self, credentials: SECLOLoginCredentials, recid: int):
        super().__init__(credentials)
        logger.debug(f'Created SECLOCitation with recid {str(recid)}')
        self.recid = recid

    def __loadCitationResultScreen(self):
        try:
            logger.debug(f'Accessing citation result window')
            self.driver.find_element(By.ID, 'ctl00_btnAudiencia').click()
            self.driver.execute_script("arguments[0].value = "+ str(self.recid)+ ";", self.driver.find_element(By.NAME, "ctl00$Top$hdnReclamoId"))
            try:
                WebDriverWait(self.driver, 2).until(False)
            except:
                pass
            logger.debug(f'Getting form for case {self.recid}')
            self.driver.find_element(By.NAME, 'ctl00$Busqueda$txtNro').send_keys(Keys.ENTER)
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
                raise NotImplementedError  

    # Gets the current list of employees registered in this claim
    # Modify this list with the results and send it to setItems 
    def getItems(self):
        logger.debug('Performing Citation getItems')
        self.__loadCitationResultScreen()
        self.fields = []
        try:
            table = self.driver.find_element(By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')
            for row in table.find_elements(By.CLASS_NAME, 'grdRowStyle'):
                self.fields.append(CitationResult(row))
            self.fields = set(self.fields)
            logger.debug(f'Found the following employees in this citation: {self.fields}')
            return self.fields
        except Exception as e:
            logger.error(f'Something happenned loading the result fields.\n{e}')
            raise InvalidCaseStateException

    # Receives a list of results per employee and presentation date, and sets the first form accordingly
    # Also advances to the second form, so that you can call for a new citation or close the case
    def setItems(self, items: CitationResult, date: datetime):
        logger.debug('Performing Citation getItems')
        self.__loadCitationResultScreen()
        try:
            for entry in set(items):
                loop = True
                while loop:
                    loop = False
                    logger.debug('Getting table contents')
                    table = self.driver.find_element(By.ID, 'ctl00_Center_grdAcuerdos_grdAcuerdos')
                    for i, row in enumerate(table.find_elements(By.CLASS_NAME, 'grdRowStyle')):
                        if (CitationResult(row) == entry 
                            and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked") 
                            and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked")
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
            if(not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'input').get_attribute("checked") 
            and not row.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'input').get_attribute("checked")):
                raise InvalidElementStateException('Incomplete selection')
        try:
            logger.info(date.strftime('%d%m%Y'))
            datefield = self.driver.find_element(By.ID, "ctl00_Center_txtFecha_txtFecha")
            for i in range(0, 10):
                datefield.send_keys(Keys.ARROW_LEFT)
            datefield.send_keys(date.strftime('%d%m%Y'))            
            self.driver.find_element(By.ID, 'ctl00_Center_btnSeguir4').click()
        except Exception as e:
            logger.error(f'error submitting form \n{e}')
            raise e
        try:
            error = self.driver.find_element(By.CLASS_NAME, 'ctl00_Center_ValidationSummary5').text
        except NoSuchElementException as e:
            pass
        except Exception as e:
            logger.warning(f'Unknown error encountered checking for errors\n{e}')
        else:
            raise ValidationException(error)
        return self
    
    def createNewCitation(self):        
        return self
    
    def closeCase(self):
        self.driver.find_element(By.ID, 'ctl00_Center_btnGrabarTotal').click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        alert = self.driver.switch_to.alert.accept()