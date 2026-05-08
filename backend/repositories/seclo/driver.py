"""
Module for interfacing with SECLO through their awful website.

This wretched thing basically frankensteins a chrome instance
and controls the website, manually loading and scraping data.
Manifest away those pesky Teams sharks.
"""

from decimal import Decimal
from pathlib import Path
import re
from time import sleep
from datetime import datetime
from typing import Any, Dict, List, Optional, Self, Set, Tuple
import os
import uuid
import logging
import requests
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidElementStateException,
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.print_page_options import PrintOptions
from webdriver_manager.chrome import ChromeDriverManager
from repositories.seclo.exceptions import (
    AttemptsExceededException,
    UnauthorizedAccessException,
    UnknownReportedException,
    RecNotAccessibleException,
    ValidationException,
    InvalidCaseStateException,
    InvalidParameterException,
    FileDownloadTimeoutException,
)
from repositories.seclo.progress import ProgressReport
from dataobjects.enums import ClaimType, PersonType, SECLOFileType
from dataobjects.seclodataclasses import (
    SECLOAddressData,
    SECLOCitation,
    SECLOClaimData,
    SECLOEmployeeData,
    SECLOEmployerData,
    SECLOLawyerData,
    SECLONotificationType,
    SECLONotificationData,
    SECLOOtherData,
    CitationResult,
)

logger = logging.getLogger(__name__)

logging.getLogger("selenium").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
logging.getLogger("WDM").setLevel(logging.CRITICAL)
PORTAL_VERSION_SUPPORTED = "8.5.4.0"

DEBUGMODE = not os.getenv("DEBUGMODE", "False") == "False"
DOWNLOADROOT = os.getenv("TEMP_DOWNLOAD_PATH", "/temp")
MAX_ATTEMPTS = 3
PRINT_OPTIONS = PrintOptions()
PRINT_OPTIONS.set_page_size(PrintOptions.A4)


class SECLOLoginCredentials:
    """
    Wrapper for exchanging login credentials between db and driver.
    """

    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password


class SECLOAccessor:
    """
    Handles the creation of the webdriver instance and auth token generation
    Other classes are meant to inherit from this.
    Provides some bullshit error handling as well, for when you get redirected to /Error.aspx.

    Parameters:
        credentials (SECLOLoginCredentials): Wrapper object containing login info.
        recid (Optional(int)): claim ID to bind accessor to. 
            Optional, but if none, must later be populated.
        progressReport (Optional(ProgressReport)): 
            an instance of ProgressReport to display progress for long calls.
    Returns:
        SECLOAccessor: Instance of chrome webdriver already logged in and ready for operations
    """

    def __init__(
        self,
        credentials: SECLOLoginCredentials,
        recid: Optional[int] = None,
        progress_report: Optional[ProgressReport] = ProgressReport(),
    ):
        self.downloadpath = Path(f"{DOWNLOADROOT}/{uuid.uuid4()}")
        self.downloadpath = self.downloadpath.resolve()
        os.mkdir(self.downloadpath)
        logger.debug("Download path set to %s", self.downloadpath)
        if DEBUGMODE:
            logger.warning(
                "WARNING! DEBUG mode enabled. Changes will not be submitted."
            )
        self.credentials = credentials
        self.recid: int | None = recid
        self.progress = progress_report if (progress_report) else ProgressReport()
        self.gde_id: str | None = None
        self._driver: WebDriver | None = None

    @property
    def driver(self: Self) -> WebDriver:
        """
        Returns running driver or raises exception.
        """
        if self._driver is not None:
            return self._driver
        raise ValueError("Driver not initialized!")

    def __enter__(self: Self) -> Self:
        chrome_options = Options()
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging"]
        )
        if os.getenv("HEADLESS", "TRUE") == "TRUE":
            logger.debug("Headless flag set true")
            chrome_options.add_argument("headless=new")
        else:
            logger.debug("Headless flag set false")

        if os.getenv("DETATCH", "FALSE") == "TRUE":
            chrome_options.add_experimental_option("detach", True)
            logger.debug("Detatch flag set true")
        else:
            logger.debug("Detatch flag set false")

        chrome_options.add_experimental_option(
            "prefs", {"download.default_directory": str(self.downloadpath)}
        )

        if os.getenv("CONTAINER", "FALSE") == "TRUE":
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
        for _ in range(0, MAX_ATTEMPTS):
            if os.getenv("CONTAINER", "FALSE") == "TRUE":
                selenium_remote = os.getenv(
                    "SELENIUM_REMOTE_URL", "http://localhost:4444/wd/hub"
                )
                self._driver = webdriver.Remote(
                    command_executor=selenium_remote, options=chrome_options
                )
            else:
                logger.debug("Creating chrome webdriver service manager instance")
                chrome_service = ChromeService(
                    executable_path=ChromeDriverManager().install()
                )

                logger.debug("instantiating chrome driver")
                self._driver = webdriver.Chrome(
                    service=chrome_service, options=chrome_options
                )
                logger.debug("Chrome loaded successfully")

            logger.debug("Getting login page...")
            self.driver.get(
                f"https://{self.credentials.user}:{self.credentials.password}"
                + "@login-int.trabajo.gob.ar/adfs/ls/wia"
                + "?wa=wsignin1.0"
                + "&wtrealm=https%3a%2f%2fconciliadores.trabajo.gob.ar%2f"
                + "&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f"
                + "&whr=https%3a%2f%2flogin-int.trabajo.gob.ar%2fadfs%2fservices%2ftrust"
            )
            logger.debug("Loading adfs")
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_Center_btnAceptar"))
                ).click()
                logger.debug("Clicked accept")
            except (TimeoutException, NoSuchElementException) as e:
                logger.debug("Logging error")
                if "adfs" in self.driver.current_url:
                    raise UnauthorizedAccessException(
                        "Password is wrong or server entered inactive hours"
                    ) from e
            logger.debug("Logged in.")
            try:
                WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "ColCerrar"))
                ).click()
                logger.debug("Closed notification panel.")
            except TimeoutException:
                logger.debug("Notification popup not found")

            logger.info(
                "Logged in as %s",
                self.driver.find_element(By.ID, "ctl00_lblConciliador").text,
            )
            portal_version = self.driver.find_element(
                By.ID, "ctl00_LblAppVersion"
            ).text.split()[1]

            if portal_version != PORTAL_VERSION_SUPPORTED:
                logger.warning(
                    "Current portal version is %s, but driver supports up to %s."
                    + "Some features might be unexpectedly broken.",
                    portal_version,
                    PORTAL_VERSION_SUPPORTED,
                )
            else:
                logger.debug("Current portal version: %s", portal_version)
            return self
        raise AttemptsExceededException("Couldn't initialize SECLO driver")

    def __exit__(self: Self, exception_type, exception_value, traceback):
        self.driver.quit()
        os.rmdir(self.downloadpath)
        # TODO delete dir contents before rmdir

    def _error_handling(self):
        """
        Function to handle redirects to /Error.aspx page.
        There's not much to be done other than display some boilerplate error message.
        But if its an auth problem the caller could choose to try again,
        so we inform this using an exception.
        """
        try:
            if "Error.aspx" in self.driver.current_url:
                error = self.driver.find_element(By.ID, "lblError").text
                if "No tiene permisos para acceder" in error:
                    raise UnauthorizedAccessException(
                        "SECLO Authorization error. "
                        + "Try initiating the request again, the token probably expired."
                    )
                raise UnknownReportedException(
                    "Unknown SECLO server error. Try initiating the request again."
                )
        except NoSuchElementException as e:
            raise InvalidElementStateException(
                "Unknown error, most likely local. idk, man."
            ) from e

    def _load_rec(self: Self):
        """
        Receives an instance of a case searchbox and populates
        the hiddenRecID field to access the case.
        This method usually does not fail.
        Searching normally has failed a few times before.

        God I hate this shit site.
        """
        if self.recid is None or self.recid == 0:
            raise InvalidParameterException("RecID Missing")

        logger.debug("Loading recID %d", self.recid)
        try:
            WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Busqueda_btnBuscar"))
            )
            self.driver.execute_script(
                "arguments[0].value = " + str(self.recid) + ";",
                self.driver.find_element(By.NAME, "ctl00$Top$hdnReclamoId"),
            )
            WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, "ctl00$Busqueda$txtNro"))
            ).send_keys(Keys.ENTER)
        except NoSuchElementException as e:
            logger.error("Couldn't find case searchbox element")
            raise e

    def set_rec_id_from_gde_id(self: Self, gde_id: str) -> Self:
        """
        Sets the current RecID to the corresponding key for the given gdeID.

        Parameters:
            gdeID: The given gdeID to find a case. eg: "EX-2020-00000000-bullshit"
        """

        self.progress.set_steps(1)
        self.progress.set_progress(0, "Setting recID")
        logger.debug("Setting recID from gdeID %s", gde_id)
        self.driver.get(
            "https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx"
        )

        gde_year = gde_id.split("-")[1]
        gde_file = gde_id.split("-")[2]
        logger.debug("gde year: %s", gde_year)
        logger.debug("gde file: %s", gde_file)
        last_exception = None
        for _ in range(0, MAX_ATTEMPTS):
            try:
                find_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_Busqueda_btnBuscar"))
                )
                self.driver.find_element(By.ID, "ctl00_Busqueda_txtNro").send_keys(
                    gde_file
                )
                self.driver.find_element(By.ID, "ctl00_Busqueda_txtAnio").send_keys(
                    Keys.ARROW_RIGHT
                    + Keys.ARROW_RIGHT
                    + Keys.ARROW_RIGHT
                    + Keys.ARROW_RIGHT
                    + Keys.BACKSPACE
                    + Keys.BACKSPACE
                    + Keys.BACKSPACE
                    + Keys.BACKSPACE
                    + gde_year
                )
                find_button.click()
            except (NoSuchElementException, TimeoutException) as e:
                logger.error("Couldn't load notifications page")
                logger.error(e)
                last_exception = e
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.ID, "ctl00_Center_grdNotificaciones")
                    )
                )
            except (NoSuchElementException, TimeoutException) as e:
                logger.error("Case with GDE ID '%s' not found", gde_id)
                logger.error(e)
                last_exception = RecNotAccessibleException("Case not found")
            rec_id = self.driver.find_element(
                By.ID, "ctl00_Top_hdnReclamoId"
            ).get_attribute("value")
            if rec_id:
                self.recid = int(rec_id)
            else:
                raise RecNotAccessibleException("Can't load recID. bummers")
            self.progress.set_completion("Done")
            logger.info("recID found, set to %s", self.recid)
            return self
        if isinstance(last_exception, RecNotAccessibleException):
            raise last_exception
        raise AttemptsExceededException(last_exception)

    def set_gde_id_from_rec_id(self: Self, rec_id: int) -> Self:
        """
        Sets the corresponding GDE ID for a given case.
        Parameters:
            rec_id (int): The recID to set a GDEID from
        Returns:
            Self:
        """
        self.driver.get(
            f"https://conciliadores.trabajo.gob.ar/Conciliador_Reclamo.aspx?RecId={rec_id}"
        )
        try:
            self.gde_id = (
                WebDriverWait(self.driver, 10)
                .until(EC.visibility_of_element_located((By.ID, "rcNroExpediente")))
                .text
            )
        except NoSuchElementException as e:
            logger.error("Case not found")
            raise RecNotAccessibleException() from e
        return self

    def set_progress(self: Self, progress: ProgressReport) -> Self:
        """
        Sets a progress reporter for this driver instance.
        Parameters:
            progress (ProgressReport): The progressReport object to override current.
        Returns:
            Self:
        """
        self.progress = progress
        return self

    def set_rec_id(self: Self, rec_id: int) -> Self:
        """
        Manually sets this driver's recID.
        Parameters:
            rec_id (int): The recID to use.
        Returns:
            Self:
        """
        self.recid = rec_id
        return self


class SECLOCitationManager(SECLOAccessor):
    """
    A browser driver class to register citation results on the SECLO site.
    Used for creating a new citation or closing a case with or without agreement.
    Most methods return self for easy chaining.
    eg. citation= SECLOCitation().setRecIDfromGDEID().reopenCase().getItems()
        citation.closeCase()
        citation.createNewCitation()

    Parameters:
        credentials(SECLOLoginCredentials): The credential instance to authorize the requests.
        recid (int | None): The recID to set for this instance. Can't be none when actually loading.
        date (datetime): The presentation date to set for the result form. Current date by default.
        progress: Instance of ProgressReport to report progress on blocking functions.
    """

    def __init__(
        self,
        credentials: SECLOLoginCredentials,
        recid: Optional[int] = None,
        date: datetime = datetime.now(),
        progress: Optional[ProgressReport] = None,
    ):
        super().__init__(credentials, recid, progress_report=progress)
        self.date = date
        self.error = None
        self.multiple = False
        self.comb_selector_length = 0
        self.comb_selector_index = 0
        self.items: List[CitationResult] = []

    def __load_citation_result_screen(self: Self) -> None:
        """
        Loads the first screen of the result form (aka selecting agreement/non-agreement)
        """
        logger.debug("Accessing citation result window")
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_btnAudiencia"))
        ).click()
        self._load_rec()
        try:
            if (
                "Registrar Resultado Audiencia"
                in WebDriverWait(self.driver, 5)
                .until(EC.visibility_of_element_located((By.ID, "ctl00_Center_tb")))
                .find_elements(By.CLASS_NAME, "appBoxMenuTitle")[1]
                .text
            ):
                if self.driver.find_element(
                    By.ID, "ctl00_Center_cmbObjetos"
                ).get_attribute("disabled"):
                    logger.debug(
                        "Claim object comb selector is disabled. This is good."
                    )
                    self.multiple = False
                else:
                    logger.debug(
                        "Claim object comb selector is enabled. This will be a bummer"
                    )
                    self.multiple = True
                    self.comb_selector_length = len(
                        Select(
                            self.driver.find_element(By.ID, "ctl00_Center_cmbObjetos")
                        ).options
                    )
                    self.comb_selector_index = 0
        except Exception as e:
            raise RecNotAccessibleException(
                f"Could not access result form for rec {self.recid}. Maybe its closed."
            ) from e

    def reopen_case(self: Self) -> Self:
        """
        Reopens a given case. Does not verify if its closed, thats the responsibility of the caller.
        Returns:
            Self:
        """
        logger.debug("Attempting to reopen case %s", str(self.recid))
        self.progress.set_steps(2)
        self.progress.set_progress(0, "Loading case for reopening")

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_lnkReabrir"))
        ).click()
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Busqueda_btnBuscar"))
        )
        self._load_rec()
        self.progress.increase_progress("Reopening case")
        try:
            # if present, case was not found
            self.driver.find_element(By.ID, "ctl00_Busqueda_grdReclamos")
        except NoSuchElementException:
            pass
        else:
            raise InvalidCaseStateException("Case not found, probably its still open")

        reopen_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_btnReabrir"))
        )
        logger.debug("Reopen button found")
        try:
            # if present, an error was raised
            error = self.driver.find_element(By.ID, "ctl00_Center_lblmensaje").text
        except NoSuchElementException:
            pass
        else:
            if error:
                raise InvalidCaseStateException(error)
        if not DEBUGMODE:
            reopen_button.click()
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        else:
            logger.warning("DEBUG MODE WON'T SUBMIT REOPENING REQUEST")
        self.progress.set_completion("Done reopening")
        return self

    def get_items(self: Self) -> List[CitationResult]:
        """
        Gets the current list of employees and employers registered in this claim.
        Modify this list with the results and new notification if needed and send it to setItems.

        Returns:
            set[CitationResult]: A set containing all the involved parts in the case.
                This set must later be populated by the caller with result and notification
                information and fed to closeCase() or createNewCitation().
        """
        self.progress.set_steps(2)
        logger.info("Performing Citation getItems")
        self.progress.set_progress(0, "Loading case")
        self.__load_citation_result_screen()
        fields = []
        fields_len = 0
        logger.debug("Case attained")

        self.progress.increase_progress("Loading items")
        try:
            table = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located(
                    (By.ID, "ctl00_Center_grdAcuerdos_grdAcuerdos")
                )
            )
            for row in table.find_elements(By.CLASS_NAME, "grdRowStyle"):
                fields.append(CitationResult(row, True))
                fields.append(CitationResult(row, False))
                fields_len += 1
            fields = set(fields)
            logger.debug("Found the following people in this citation:")
            for field in fields:
                logger.debug(field)
            self.progress.set_completion("Done getting items.")
            items = []
            for item in fields:
                items.append(item)
            return items
        except Exception as e:
            raise InvalidCaseStateException(
                "Something bad happenned loading the result fields."
            ) from e

    def __row_populated_check(self: Self, row: WebElement) -> bool:
        """
        Checks whether a row from citation result screen is populated already.

        Parameters:
            row(WebElement): A table row selected from the result screen
        Returns:
            bool: Whether the row is populated or not
        """
        return not row.find_elements(By.TAG_NAME, "td")[2].find_elements(
            By.TAG_NAME, "td"
        )[1].find_element(By.TAG_NAME, "input").get_attribute(
            "checked"
        ) and not row.find_elements(
            By.TAG_NAME, "td"
        )[2].find_elements(
            By.TAG_NAME, "td"
        )[0].find_element(
            By.TAG_NAME, "input"
        ).get_attribute(
            "checked"
        )

    def __get_matching_rows(self, entry: CitationResult) -> List[Tuple[int, WebElement]]:
        '''
        For a given entry, finds all matching rows.
        Parameters:
            entry (CitationResult): Entry to search for. Can only be employee.
        Returns:
            list: A list containing a (idx, WebEntry) tuple for every row matched
        '''
        rows = []
        logger.info("Getting table contents")
        table = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located(
                (By.ID, "ctl00_Center_grdAcuerdos_grdAcuerdos")
            )
        )
        for i, row in enumerate(table.find_elements(By.CLASS_NAME, "grdRowStyle")):
            # check if matches
            if (
                CitationResult(row) == entry
                and self.__row_populated_check(row)
                and entry.enabled
                and CitationResult(row).enabled
            ):
                rows.append((i, row))
        return rows

    def __set_item(self: Self, entry: CitationResult):
        loop = True
        while loop:
            loop = False
            rows = self.__get_matching_rows(entry)
            self.progress.increase_progress("Setting results...")
            for i, row in rows:
                logger.debug("Row %d matches %s and is unselected, applying", i, entry)
                if entry.amount:
                    # Set agreement
                    logger.info("Agreement for %s", entry)
                    (
                        row.find_elements(By.TAG_NAME, "td")[2]
                        .find_elements(By.TAG_NAME, "td")[0]
                        .find_element(By.TAG_NAME, "label")
                        .click()
                    )
                    # Wait until refreshed
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_Center_btnSeguir4"))
                    )
                    # Flag so we iterate again, there may be another row for employee
                    # Yes, this site sucks, i'm well aware of that, even moreso by now
                    loop = True

                    # We refreshed so we must search rows again
                    WebDriverWait(self.driver, 5).until(EC.staleness_of(row))
                    for row2 in self.driver.find_element(
                        By.ID, "ctl00_Center_grdAcuerdos_grdAcuerdos"
                    ).find_elements(By.CLASS_NAME, "grdRowStyle"):
                        if (
                            row2.find_elements(By.TAG_NAME, "td")[2]
                            .find_elements(By.TAG_NAME, "td")[0]
                            .find_element(By.TAG_NAME, "input")
                            .get_attribute("checked")
                            and len(
                                row2.find_elements(By.TAG_NAME, "td")[4]
                                .find_element(By.TAG_NAME, "input")
                                .text
                            )
                            == 0
                        ):
                            # Matches, so populate amount
                            (
                                row2.find_elements(By.XPATH, "./*")[4]
                                .find_element(By.TAG_NAME, "input")
                                .send_keys(entry.amount.replace(".", ","))
                            )
                            break
                    else:
                        raise InvalidCaseStateException(
                            "Couldn't find amount input for case result"
                        )
                else:
                    # set non-agreement
                    logger.info("Non-agreement for %s", entry)
                    (
                        row.find_elements(By.TAG_NAME, "td")[2]
                        .find_elements(By.TAG_NAME, "td")[1]
                        .find_element(By.TAG_NAME, "input")
                        .click()
                    )
                    loop = True
                    break

    def __set_items(self: Self, ignore_multiple_comb: bool = False) -> Self:
        logger.info("Performing Citation getItems")
        self.__load_citation_result_screen()

        if self.multiple:
            if self.comb_selector_index == self.comb_selector_length:
                logger.debug("Done setting items.")
                return self.__advance_result_form()
            else:
                Select(
                    WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_Center_cmbObjetos"))
                    )
                ).select_by_index(self.comb_selector_index)
                logger.debug(
                    "Selected comb level entry %d of %d",
                    self.comb_selector_index + 1,
                    self.comb_selector_length,
                )
                self.comb_selector_index += 1
        self.progress.set_steps(
            1
            + (
                (
                    1
                    if ignore_multiple_comb or not self.multiple
                    else self.comb_selector_length
                )
                * (len(self.items) + 1)
            )
        )
        try:
            for entry in set(self.items):
                if entry.is_employee():
                    self.__set_item(entry)
        except (NoSuchElementException, TimeoutException):
            self._error_handling()
        for row in (
            WebDriverWait(self.driver, 5)
            .until(
                EC.visibility_of_element_located(
                    (By.ID, "ctl00_Center_grdAcuerdos_grdAcuerdos")
                )
            )
            .find_elements(By.CLASS_NAME, "grdRowStyle")
        ):
            if self.__row_populated_check(row):
                raise InvalidElementStateException("Incomplete selection")
        return self.__advance_result_form()

    def __fill_date_input(self: Self, input_id: str, date: datetime):
        logger.info(self.date.strftime("%d%m%Y"))
        datefield = self.driver.find_element(By.ID, input_id)
        for _ in range(0, 10):
            datefield.send_keys(Keys.ARROW_LEFT)
        datefield.send_keys(date.strftime("%d%m%Y"))

    def __advance_result_form(self: Self):
        try:
            self.__fill_date_input("ctl00_Center_txtFecha_txtFecha", self.date)
            self.driver.find_element(By.ID, "ctl00_Center_btnSeguir4").click()
        except NoSuchElementException as e:
            logger.error("error submitting form")
            raise e
        self.__validation_error_checker()
        return self

    def __validation_error_checker(self: Self):
        try:
            self.error = self.driver.find_element(
                By.CLASS_NAME, "ctl00_Center_lblError"
            ).text
        except NoSuchElementException:
            # Expected, means no errors
            pass
        else:
            raise ValidationException(self.error)

        try:
            self.error = self.driver.find_element(
                By.CLASS_NAME, "ctl00_Center_ValidationSummary5"
            ).text
        except NoSuchElementException:
            # Expected, means no errors
            pass
        else:
            raise ValidationException(self.error)

    def create_new_citation(self: Self, items: Set[CitationResult], date: datetime):
        """
        Receives a modified items set with the appropiate result
        and notification data, plus a date, and registers a new citation.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (Set[CitationResult]): The set provided by getItems with attributes set.
            date: The date and time requested for the new citation.
        """
        self.items = list(items)
        self.__set_items(True)
        absent_citation = False
        self.progress.increase_progress("Setting new citation date")
        for item in self.items:
            if item.absent:
                absent_citation = True
        if absent_citation:
            self.driver.find_element(
                By.ID, "ctl00_Center_btnNuevaIncomparecencia"
            ).click()
        else:
            self.driver.find_element(By.ID, "ctl00_Center_btnNuevaAudiencia").click()
        self.__fill_date_input("ctl00$Center$txtFecha$txtFecha", date)

        Select(
            self.driver.find_element(By.ID, "ctl00_Center_cmbHoras")
        ).select_by_visible_text(f"{date.hour:02}")
        Select(
            self.driver.find_element(By.ID, "ctl00_Center_cmbMinutos")
        ).select_by_visible_text(f"{(date.minute - date.minute % 5):02}")

        for row in self.driver.find_element(
            By.ID, "ctl00_Center_grdTrabajadores"
        ).find_elements(By.CLASS_NAME, "grdRowStyle"):
            for entry in self.items:
                if (
                    row.find_elements(By.TAG_NAME, "td")[0].text in entry.get_person()
                    and row.find_elements(By.TAG_NAME, "td")[1].text
                    in entry.get_person()
                ):
                    if entry.absent:
                        (
                            row.find_elements(By.TAG_NAME, "td")[2]
                            .find_element(By.TAG_NAME, "input")
                            .click()
                        )
                    if entry.notify:
                        if absent_citation:
                            (
                                row.find_elements(By.TAG_NAME, "td")[3]
                                .find_element(By.TAG_NAME, "input")
                                .click()
                            )
                        (
                            Select(
                                row.find_elements(By.TAG_NAME, "td")[
                                    4 if absent_citation else 2
                                ].find_element(By.TAG_NAME, "select")
                            ).select_by_value(entry.notif_method.value)
                        )
                    break
        for row in self.driver.find_element(
            By.ID, "ctl00_Center_grdEmpleadores"
        ).find_elements(By.CLASS_NAME, "grdRowStyle"):
            for entry in self.items:
                if row.find_elements(By.TAG_NAME, "td")[0].text in entry.get_person():
                    if entry.absent:
                        (
                            row.find_elements(By.TAG_NAME, "td")[1]
                            .find_element(By.TAG_NAME, "input")
                            .click()
                        )
                    if entry.notify:
                        if absent_citation:
                            (
                                row.find_elements(By.TAG_NAME, "td")[2]
                                .find_element(By.TAG_NAME, "input")
                                .click()
                            )
                        (
                            Select(
                                row.find_elements(By.TAG_NAME, "td")[
                                    3 if absent_citation else 1
                                ].find_element(By.TAG_NAME, "select")
                            ).select_by_value(entry.notif_method.value)
                        )

        if not DEBUGMODE:
            self.driver.find_element(By.ID, "ctl00_Center_btnGrabar").click()
            self.__validation_error_checker()
        else:
            logger.warning(
                "DEBUG MODE WON'T PERSIST NEW CITATION. "
                + "However, this citation will be 'completed' rather than 'pending'"
            )
        self.progress.set_completion("Done new citation request")

    def close_case(self: Self, items: set[CitationResult]):
        """
        Sets the claim results based on the items and then closes the case.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (set[CitationResult]): The modified set provided by getItems with results set.
        """
        self.items = list(items)
        if self.multiple:
            while self.comb_selector_index < self.comb_selector_length:
                self.__set_items(False)
                self.progress.increase_progress("Closing partial claim")
                if not DEBUGMODE:
                    self.driver.find_element(
                        By.ID, "ctl00_Center_btnGrabarTotal"
                    ).click()
                    WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                    self.driver.switch_to.alert.accept()
        else:
            self.__set_items(False)
            self.progress.increase_progress("Closing claim")
            if not DEBUGMODE:
                self.driver.find_element(By.ID, "ctl00_Center_btnGrabarTotal").click()
                WebDriverWait(self.driver, 10).until(EC.alert_is_present())
                self.driver.switch_to.alert.accept()
            else:
                logger.warning("DEBUG MODE WON'T SUBMIT CLOSE REQUEST.")
        self.progress.set_completion("Done closing claim")


class SECLOFileManager(SECLOAccessor):
    """
    A class to handle file management,
    including querying and downloading already present files,
    uploading new ones, or uploading records.

    Parameters:
        credentials: The wrapper object containing the login information.
        recid: Tha claim number to bind to this instance.
    """

    def __init__(
        self: Self, credentials: SECLOLoginCredentials, recid: Optional[int] = None
    ):
        super().__init__(credentials, recid)
        self.file_list = self.__get_files()

    def __get_files(self: Self):
        """
        Populates internal object storage with the current files in rec.
        idc about congruency, this is a throwaway object that expires quickly.
        """
        self.driver.get(
            f"https://conciliadores.trabajo.gob.ar/Documentacion_Adjunta.aspx?RecId={self.recid}"
        )
        files: List[Tuple[str, str, datetime]] = []
        for row in self.driver.find_element(By.ID, "grdDocumentos").find_elements(
            By.CLASS_NAME, "grdRowStyle"
        ):
            files.append(
                (
                    row.find_elements(By.TAG_NAME, "td")[0].text,
                    row.find_elements(By.TAG_NAME, "td")[1].text,
                    self.__shit_date_to_datetime(
                        row.find_elements(By.TAG_NAME, "td")[2].text
                    ),
                )
            )
            logger.debug(files[-1])
        return files

    def get_files(self: Self) -> List[Tuple[str, str, datetime]]:
        """
        Gets a list of all the registered files currently uploaded to this rec.

        Returns:
            files (Tuple[str, str, datetime]): (type, description, date)
        """
        return self.file_list[:]

    def get_file(self: Self, index: int) -> Path:
        """
        Request a given file from the list of uploaded file.

        Parameters:
            index (int): The index of the requested file
        Returns:
            Nothing currently, but hopefully later a handle to the downloaded file.
            It's downloaded to a temp directory so you can go look for it tho.
        """

        if index >= len(self.file_list) or index < 0:
            raise IndexError("Requesting a file beyond bounds")
        self.get_files()
        logger.debug("Downloading file")
        download = (
            self.driver.find_element(By.ID, "grdDocumentos")
            .find_elements(By.CLASS_NAME, "grdRowStyle")[index]
            .find_elements(By.TAG_NAME, "td")[3]
            .find_element(By.TAG_NAME, "input")
        )
        logger.info(download.get_attribute("title"))
        # Hardcoded name (for this page at least)
        # Selenium doesn't really offer a solution for downloading files
        # and curl is useless for this (bc asp stuff, why is it like this??).
        downloadfile = self.downloadpath / "Reporte.pdf"
        downloadfile.unlink(True)
        download.click()
        for _ in range(0, 200):
            if downloadfile.exists():
                return downloadfile
            else:
                sleep(0.1)
        raise FileDownloadTimeoutException(
            "Timeout while trying to download file, try again later."
        )

    def upload_file(
        self: Self,
        file: str,
        filetype: SECLOFileType,
        description: Optional[str] = None,
    ) -> None:
        """
        Uploads a file. Works for everything except records,
        which are uploaded using the uploadRecord method because
        its completely different for some godforsaken reason.
        Parameters:
            file (str): The path to the file to be uploaded. Must be a PDF.
            filetype: The given filetype to upload, from the enum.
            description: Only used when uploading a 'other' type of file.
        """
        self.driver.get(
            "https://conciliadores.trabajo.gob.ar/"+\
            f"Documentacion_ParaAdjuntar.aspx?RecId={self.recid}"
        )

        Select(
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "Tipo_Documentacion"))
            )
        ).select_by_value(filetype.value[0])
        if filetype.value[1] is True:
            if description is None:
                raise InvalidParameterException(
                    "Description cannot be null for this type of file"
                )
            (
                WebDriverWait(self.driver, 5)
                .until(EC.presence_of_element_located((By.ID, "txtDescripcion")))
                .send_keys(description)
            )
        (
            WebDriverWait(self.driver, 2)
            .until(EC.element_to_be_clickable((By.ID, "Archivo")))
            .send_keys(file)
        )
        (
            WebDriverWait(self.driver, 2)
            .until(EC.element_to_be_clickable((By.ID, "btnAgregar")))
            .click()
        )

        # Save button (why tf is it unlabeled?? This is some lousy website coding)
        if not DEBUGMODE:
            save = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "Button1"))
            )
            save.click()
            WebDriverWait(self.driver, 5).until(EC.staleness_of(save))
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "Button1"))
            )

            error_str = (
                self.driver.find_element(By.CLASS_NAME, "ingreso")
                .find_elements(By.TAG_NAME, "tr")[1]
                .text.strip()
            )
            if error_str:
                raise ValidationException(f"Error uploading file: {error_str}")
        else:
            logger.warning("FILE WON'T BE SAVED IN DEBUG MODE!")
        self.__get_files()

    def upload_record(
        self: Self, file: str, agreement: bool, override: bool = False
    ) -> None:
        """
        Uploads a record to an already closed case.
        Parameters:
            file (str): Path to the desired record to upload.
            agreement (bool): Whether its an agreement or not,
                because the way of uploading them is different for some godforsaken reason.
        """
        if not self.gde_id:
            if self.recid:
                self.set_gde_id_from_rec_id(self.recid)
            else:
                raise InvalidParameterException("Missing recID and gdeID")
        logger.info(self.gde_id)

        self.driver.get("https://conciliadores.trabajo.gob.ar/Novedades.aspx")
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_btnActa"))
        ).click()
        load_next_page = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_btnBuscar"))
        )
        if agreement:
            self.driver.find_element(By.ID, "ctl00_Center_radTipo_0").click()
        else:
            self.driver.find_element(By.ID, "ctl00_Center_radTipo_1").click()
        load_next_page.click()

        table = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_grdReclamos"))
        )
        try:
            record_list = table.find_elements(By.CLASS_NAME, "grdRowStyle")
        except NoSuchElementException as e:
            raise InvalidElementStateException(
                "There are no elements available to upload records here. That sucks, man."
            ) from e

        for row in record_list:
            if row.find_elements(By.TAG_NAME, "td")[0].text.strip() == self.gde_id:
                try:
                    row.find_elements(By.TAG_NAME, "td")[2].find_element(
                        By.TAG_NAME, "input"
                    )
                    logger.warning(
                        "Claim %s already has record uploaded (%s)",
                        self.gde_id,
                        "agreement" if agreement else "nonagreement",
                    )
                    if not override:
                        return
                except NoSuchElementException:
                    # Expected if not uploaded
                    continue
                (
                    row.find_elements(By.TAG_NAME, "td")[3]
                    .find_element(By.TAG_NAME, "input")
                    .send_keys(file)
                )
                break
        else:
            raise InvalidElementStateException(
                "Given claim does not have record uploading enabled right now."
            )

        if not DEBUGMODE:
            self.driver.find_element(By.ID, "ctl00_Center_btnGenerar").click()
            WebDriverWait(self.driver, 15).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_grdReclamos"))
            )
        else:
            logger.warning("WON'T UPLOAD RECORD IN UPLOAD MODE!")
        return

    def __shit_date_to_datetime(self: Self, date: str) -> datetime:
        """
        receives a date in a weird ugly format like 30/dic./2024
        and returns a proper datetime object for it
        my god i hate this
        """
        months = [
            "ene",
            "feb",
            "mar",
            "abr",
            "may",
            "jun",
            "jul",
            "ago",
            "sep",
            "oct",
            "nov",
            "dec",
        ]
        day = int(date.split("/")[0])
        month = date.split("/")[1]
        year = int(date.split("/")[2])
        new_month = 0
        for idx, month_name in enumerate(months):
            if month_name in month:
                new_month = idx + 1
                break
        return datetime(day=day, month=new_month, year=year)


class SECLORecData(SECLOAccessor):
    """
    A class for accessing data from claims, the main data ingestion class if you may.
    Eventually may allow modifying data as well,
    but the website is so shit I don't think it'll be reliable.
    """

    def get_notification_data(
        self: Self, gde_id: Optional[str] = None
    ) -> List[SECLONotificationData]:
        """
        Gets the associated notification information for a given case.
        Its up to the caller to link those to a citation or stuff like that.

        Returns:
            List[SECLONotificationData]: The list of notification entries.
        """

        if gde_id:
            self.set_rec_id_from_gde_id(gde_id=gde_id)
        else:
            self.driver.get(
                "https://conciliadores.trabajo.gob.ar/O_ConsultaNotificaciones.aspx"
            )
            self._load_rec()

        self.progress.set_steps(1)

        results = []
        table = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_Center_grdNotificaciones"))
        )
        for row in table.find_elements(By.CLASS_NAME, "grdRowStyle"):
            results.append(
                SECLONotificationData(
                    id=int(row.find_elements(By.TAG_NAME, "td")[0].text),
                    person=row.find_elements(By.TAG_NAME, "td")[1].text,
                    citationType=row.find_elements(By.TAG_NAME, "td")[2].text,
                    isEmployer=row.find_elements(By.TAG_NAME, "td")[3].text == "Emp",
                    notificationType=SECLONotificationType.notification_short_to_enum(
                        row.find_elements(By.TAG_NAME, "td")[4].text
                    ),
                    generatedDate=datetime.strptime(
                        row.find_elements(By.TAG_NAME, "td")[5].text, "%d/%m/%Y"
                    ),
                    notifiedDate=(
                        None
                        if len(row.find_elements(By.TAG_NAME, "td")[6].text) == 0
                        else datetime.strptime(
                            row.find_elements(By.TAG_NAME, "td")[6].text, "%d-%m-%Y"
                        )
                    ),
                    notificationCode=row.find_elements(By.TAG_NAME, "td")[7].text,
                    notificationStatus=row.find_elements(By.TAG_NAME, "td")[8].text,
                    afipRead="Si" in row.find_elements(By.TAG_NAME, "td")[9].text,
                    citationDate=datetime.strptime(
                        row.find_elements(By.TAG_NAME, "td")[10].text, "%d/%m/%Y %H:%M"
                    ),
                    citationStatus=row.find_elements(By.TAG_NAME, "td")[11].text,
                )
            )

        self.progress.set_completion(f"Found notif data for {self.recid}")
        return results

    def __save_claim_data(self: Self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_lnkFinalizar"))
        ).click()
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_btnAceptarRec"))
        ).click()
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_btnSi"))
        ).click()
        WebDriverWait(self.driver, 10).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()

    def get_claim_data(self: Self) -> SECLOClaimData:
        """
        Accesses the given claims initiation data.
        Useful to get names, IDs, employment parameters, etc.

        Returns:
            SECLOClaimData: an object that contains all claim data.
        """
        attempts = 0
        last_exception = None
        while attempts < MAX_ATTEMPTS:
            try:
                self.progress.set_steps(1)
                self.progress.set_progress(0, "Loading claim data form...")
                WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_lnkModificacion"))
                ).click()
                self._load_rec()
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.ID, "ctl00_Center_ucReclamo_txtFecha")
                    )
                )
                seclo_db_ok = True
                total_items = len(
                    WebDriverWait(self.driver, 10)
                    .until(
                        EC.element_to_be_clickable(
                            (By.ID, "ctl00_Center_lstTrabajadores")
                        )
                    )
                    .find_elements(By.TAG_NAME, "li")
                )
                total_items += len(
                    WebDriverWait(self.driver, 10)
                    .until(
                        EC.element_to_be_clickable(
                            (By.ID, "ctl00_Center_lstEmpleadores")
                        )
                    )
                    .find_elements(By.TAG_NAME, "li")
                )
                total_items += len(
                    WebDriverWait(self.driver, 10)
                    .until(
                        EC.element_to_be_clickable(
                            (By.ID, "ctl00_Center_lstReprentantes")
                        )
                    )
                    .find_elements(By.TAG_NAME, "li")
                )
                try:
                    total_items += len(
                        WebDriverWait(self.driver, 1)
                        .until(
                            EC.element_to_be_clickable(
                                (By.ID, "ctl00_Center_lstDerechohabientes")
                            )
                        )
                        .find_elements(By.TAG_NAME, "li")
                    )
                except (NoSuchElementException, TimeoutException):
                    pass
                self.progress.set_steps(2 + total_items)

                # CLAIM
                self.progress.increase_progress("Getting claim data...")
                init_by_employee = self.driver.find_element(
                    By.ID, "ctl00_Center_ucReclamo_optReclamante_0"
                ).get_attribute("checked")
                claim_data = SECLOClaimData(
                    recid=self.recid or 0,
                    legal_stuff=self.driver.find_element(
                        By.ID, "ctl00_Center_ucReclamo_txtComentario"
                    ).get_attribute("value")
                    or "",
                    init_by_worker=init_by_employee == "true" or init_by_employee is True,
                )
                for row in self.driver.find_element(
                    By.ID, "ctl00_Center_ucReclamo_chkObjetoReclamo"
                ).find_elements(By.TAG_NAME, "td"):
                    if row.find_element(By.TAG_NAME, "input").get_attribute("checked"):
                        claim_data.add_claim_object(
                            ClaimType.string_to_enum(
                                row.find_element(By.TAG_NAME, "label").text
                            )
                        )

                # EMPLOYEES
                count = len(
                    self.driver.find_element(
                        By.ID, "ctl00_Center_lstTrabajadores"
                    ).find_elements(By.TAG_NAME, "li")
                )
                i = 0
                while i < count:
                    employees = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_lstTrabajadores")
                        )
                    )
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            employees.find_elements(By.TAG_NAME, "li")[i].find_element(
                                By.TAG_NAME, "a"
                            )
                        )
                    ).click()

                    cuil = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_ctl00_cuit_txtC")
                        )
                    )
                    name = f'{self.driver
                              .find_element(By.ID, 'ctl00_Center_ctl00_txtApellido_txt')
                              .get_attribute('value') or ""
                            } {self.driver
                              .find_element(By.ID, 'ctl00_Center_ctl00_txtNombre_txt')
                              .get_attribute('value') or ""}'
                    self.progress.increase_progress(
                        f"Employee {name} ({i+1} of {count})"
                    )

                    if (
                        len(cuil.text) > 0
                        and seclo_db_ok
                        and not cuil.get_attribute("disabled")
                    ):
                        cuil.click()
                        cuil.send_keys(Keys.TAB)
                        (
                            WebDriverWait(self.driver, 5).until(
                                lambda driver: len(
                                    driver.find_element(
                                        By.ID, "ctl00_Center_ctl00_cuit_txtRS"
                                    ).get_attribute("value")
                                    or ""
                                )
                                > 0
                            )
                        )
                        if "null null" not in (
                            self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_cuit_txtRS"
                            ).get_attribute("value")
                            or ""
                        ):
                            name = (
                                self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl00_cuit_txtRS"
                                ).get_attribute("value")
                                or ""
                            )
                        else:
                            seclo_db_ok = False
                    employee = SECLOEmployeeData(
                        name=name,
                        dni=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS"
                        ).get_attribute("value")
                        or "",
                        cuil=(cuil.get_attribute("value") or "").replace("-", ""),
                        validated=seclo_db_ok,
                    )
                    employee.add_address(
                        SECLOAddressData(
                            province=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtProvincia"
                            ).get_attribute("value")
                            or "",
                            district=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtPartido"
                            ).get_attribute("value")
                            or "",
                            county=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtLocalidad"
                            ).get_attribute("value")
                            or "",
                            street=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtCalle"
                            ).get_attribute("value")
                            or "",
                            number=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtNumero"
                            ).get_attribute("value"),
                            floor=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtPiso"
                            ).get_attribute("value"),
                            apt=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtDepart"
                            ).get_attribute("value"),
                            cpa=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtCPA"
                            ).get_attribute("value"),
                            bonus_data=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl00_Domicilio_direc_txtAdicional"
                            ).get_attribute("value"),
                        )
                    )
                    employee.add_birth_date(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtFecNacimiento_txt"
                        ).get_attribute("value")
                        or ""
                    )
                    employee.add_claim_amount(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtImporte_txt"
                        ).get_attribute("value")
                        or ""
                    )
                    employee.add_mail(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtEmail_txt"
                        ).get_attribute("value")
                    )
                    employee.add_mobile_phone(
                        prefix=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtCodArea_Numerico"
                        ).get_attribute("value")
                        or "",
                        phone=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtCel_Numerico"
                        ).get_attribute("value")
                        or "",
                    )
                    employee.add_phone(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtTelefono_txt"
                        ).get_attribute("value")
                    )
                    employee.add_start_date(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtFecIngreso_txt"
                        ).get_attribute("value")
                        or ""
                    )
                    employee.add_end_date(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtFecEgreso_txt"
                        ).get_attribute("value")
                        or ""
                    )
                    employee.add_type(
                        cct=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtConvenioNum_txt"
                        ).get_attribute("value")
                        or "",
                        category=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtCategoria_txt"
                        ).get_attribute("value"),
                    )
                    employee.add_wage(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl00_txtRemuneracion_txt"
                        ).get_attribute("value")
                        or ""
                    )
                    claim_data.add_employee(employee)
                    if seclo_db_ok:
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.ID, "ctl00_Center_ctl00_btnAgregar")
                            )
                        ).click()
                    i += 1

                # EMPLOYERS
                count = len(
                    self.driver.find_element(
                        By.ID, "ctl00_Center_lstEmpleadores"
                    ).find_elements(By.TAG_NAME, "li")
                )
                i = 0
                while i < count:
                    employers = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_lstEmpleadores")
                        )
                    )
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            employers.find_elements(By.TAG_NAME, "li")[i].find_element(
                                By.TAG_NAME, "a"
                            )
                        )
                    ).click()

                    WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_ctl01_cuit_txtRS")
                        )
                    )
                    name = (
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl01_cuit_txtRS"
                        ).get_attribute("value")
                        or ""
                    )
                    self.progress.increase_progress(
                        f"Employer {name} ({i+1} of {count})..."
                    )
                    cuil = (
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl01_cuit_txtC"
                        ).get_attribute("value")
                        or ""
                    ).replace("-", "")
                    dni = self.driver.find_element(
                        By.ID, "ctl00_Center_ctl01_txtNroDocumento_txt"
                    ).get_attribute("value")
                    employer = SECLOEmployerData(
                        name=name,
                        dni=dni,
                        cuil=cuil,
                        validated=seclo_db_ok and (len(cuil) > 0),
                    )
                    employer.add_address(
                        SECLOAddressData(
                            province=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtProvincia"
                            ).get_attribute("value")
                            or "",
                            district=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtPartido"
                            ).get_attribute("value")
                            or "",
                            county=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtLocalidad"
                            ).get_attribute("value")
                            or "",
                            street=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtCalle"
                            ).get_attribute("value")
                            or "",
                            number=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtNumero"
                            ).get_attribute("value"),
                            floor=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtPiso"
                            ).get_attribute("value"),
                            apt=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtDepart"
                            ).get_attribute("value"),
                            cpa=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtCPA"
                            ).get_attribute("value"),
                            bonus_data=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtAdicional"
                            ).get_attribute("value"),
                        )
                    )
                    employer.add_mail(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl01_txtEmail_txt"
                        ).get_attribute("value")
                    )
                    for item in self.driver.find_element(
                        By.ID, "ctl00_Center_ctl01_cmbTipoSociedad_cmb"
                    ).find_elements(By.TAG_NAME, "option"):
                        if item.get_attribute("selected"):
                            employer.add_person_type(PersonType.from_string(item.text))
                    employer.add_phone(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl01_txtTelefono_txt"
                        ).get_attribute("value")
                    )
                    claim_data.add_employer(employer)
                    if seclo_db_ok:
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.ID, "ctl00_Center_ctl01_btnAgregar")
                            )
                        ).click()
                    i += 1

                # LAWYERS
                count = len(
                    self.driver.find_element(
                        By.ID, "ctl00_Center_lstReprentantes"
                    ).find_elements(By.TAG_NAME, "li")
                )
                i = 0
                while i < count:
                    lawyers = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_lstReprentantes")
                        )
                    )
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            lawyers.find_elements(By.TAG_NAME, "li")[i].find_element(
                                By.TAG_NAME, "a"
                            )
                        )
                    ).click()

                    email = (
                        self.driver.find_element(
                            By.ID, "ctl00_Center_ctl02_txtEmail_txt"
                        ).get_attribute("value")
                        or ""
                    ).strip()
                    phone = self.driver.find_element(
                        By.ID, "ctl00_Center_ctl02_txtTelefono_txt"
                    ).get_attribute("value")
                    mobileprefix = self.driver.find_element(
                        By.ID, "ctl00_Center_ctl02_txtCodArea_Numerico"
                    ).get_attribute("value")
                    mobilephone = self.driver.find_element(
                        By.ID, "ctl00_Center_ctl02_txtCel_Numerico"
                    ).get_attribute("value")

                    # name validation (unreliable!)
                    # folio = WebDriverWait(self.driver, 5).until(
                    #   EC.visibility_of_element_located((By.ID, 'ctl00_Center_ctl02_txtFolio_txt'))
                    # )
                    # foliovalue = folio.get_property('value')
                    # folio.send_keys(
                    #   Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT + Keys.ARROW_RIGHT +
                    #   Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE +
                    #   '0' + Keys.TAB)
                    # WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    # self.driver.switch_to.alert.accept()
                    # folio.send_keys(str(foliovalue))
                    # folio.send_keys(Keys.TAB)
                    self_validated = True
                    name: str = " ".join(
                        [
                            self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_txtNombre_lbl"
                            ).text,
                            self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_txtApellido_lbl"
                            ).text,
                        ]
                    )
                    # try:
                    #     WebDriverWait(self.driver, 5).until(
                    #         lambda driver: len(driver
                    #             .find_element(By.ID, 'ctl00_Center_ctl02_txtNombre_lbl').text)>0)
                    # except Exception:
                    #     try:
                    #         alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    #         self.driver.switch_to.alert.accept()
                    #     except Exception:
                    #         selfValidated = False
                    # if selfValidated:
                    #     name:str = " ".join([
                    #       self.driver.find_element(By.ID,"ctl00_Center_ctl02_txtNombre_lbl").text,
                    #    self.driver.find_element(By.ID,"ctl00_Center_ctl02_txtApellido_lbl").text])
                    self.progress.increase_progress(
                        f"Lawyer {name} ({i+1} of {count})..."
                    )

                    lawyer = SECLOLawyerData(
                        name=name,
                        dni=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl02_txtNroDocumento_lbl"
                        ).text,
                        validated=seclo_db_ok and self_validated,
                    )
                    lawyer.add_address(
                        SECLOAddressData(
                            province=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtProvincia"
                            ).get_attribute("value")
                            or "",
                            district=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtPartido"
                            ).get_attribute("value")
                            or "",
                            county=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtLocalidad"
                            ).get_attribute("value")
                            or "",
                            street=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtCalle"
                            ).get_attribute("value")
                            or "",
                            number=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtNumero"
                            ).get_attribute("value"),
                            floor=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtPiso"
                            ).get_attribute("value"),
                            apt=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtDepart"
                            ).get_attribute("value"),
                            cpa=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtCPA"
                            ).get_attribute("value"),
                            bonus_data=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl02_Domicilio_direc_txtAdicional"
                            ).get_attribute("value"),
                        )
                    )

                    for row in self.driver.find_element(
                        By.ID, "ctl00_Center_ctl02_lstAsignados"
                    ).find_elements(By.TAG_NAME, "td"):
                        if row.find_element(By.TAG_NAME, "input").get_attribute(
                            "checked"
                        ):
                            name = row.text.replace(",", "")
                            lawyer.add_represented(
                                is_employee=self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl02_chkRepresentantes_0"
                                ).get_attribute("checked")
                                is True,
                                name=name,
                            )
                    lawyer.add_phone(phone)
                    lawyer.add_mobile_phone(
                        prefix=mobileprefix or "", phone=mobilephone or ""
                    )
                    lawyer.add_mail(email)
                    lawyer.add_tf(
                        t=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl02_txtTomo_txt"
                        ).get_attribute("value")
                        or "",
                        f=self.driver.find_element(
                            By.ID, "ctl00_Center_ctl02_txtFolio_txt"
                        ).get_attribute("value")
                        or "",
                    )
                    claim_data.add_lawyer(lawyer)
                    i += 1

                # OTHERS
                try:
                    count = len(
                        self.driver.find_element(
                            By.ID, "ctl00_Center_lstDerechohabientes"
                        ).find_elements(By.TAG_NAME, "li")
                    )
                except NoSuchElementException:
                    pass
                else:
                    i = 0
                    while i < count:
                        employees = WebDriverWait(self.driver, 5).until(
                            EC.visibility_of_element_located(
                                (By.ID, "ctl00_Center_lstDerechohabientes")
                            )
                        )
                        WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable(
                                employees.find_elements(By.TAG_NAME, "li")[
                                    i
                                ].find_element(By.TAG_NAME, "a")
                            )
                        ).click()
                        WebDriverWait(self.driver, 5).until(
                            EC.visibility_of_element_located(
                                (By.ID, "ctl00_Center_ctl03_txtNombre_txt")
                            )
                        )
                        name = " ".join(
                            [
                                self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl03_txtApellido_txt"
                                ).get_attribute("value")
                                or "",
                                self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl03_txtNombre_txt"
                                ).get_attribute("value")
                                or "",
                            ]
                        )
                        dni = self.driver.find_element(
                            By.ID, "ctl00_Center_ctl03_txtNroDocumento_txt"
                        ).get_attribute("value")
                        self.progress.increase_progress(
                            f"Other {name} ({i+1} of {count})..."
                        )
                        other = SECLOOtherData(name=name, dni=dni)
                        other.add_address(
                            SECLOAddressData(
                                province=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtProvincia",
                                ).get_attribute("value")
                                or "",
                                district=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtPartido",
                                ).get_attribute("value")
                                or "",
                                county=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtLocalidad",
                                ).get_attribute("value")
                                or "",
                                street=self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl03_Domicilio_direc_txtCalle"
                                ).get_attribute("value")
                                or "",
                                number=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtNumero",
                                ).get_attribute("value"),
                                floor=self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl03_Domicilio_direc_txtPiso"
                                ).get_attribute("value"),
                                apt=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtDepart",
                                ).get_attribute("value"),
                                cpa=self.driver.find_element(
                                    By.ID, "ctl00_Center_ctl03_Domicilio_direc_txtCPA"
                                ).get_attribute("value"),
                                bonus_data=self.driver.find_element(
                                    By.ID,
                                    "ctl00_Center_ctl03_Domicilio_direc_txtAdicional",
                                ).get_attribute("value"),
                            )
                        )
                        other.add_mail(
                            self.driver.find_element(
                                By.ID, "ctl00_Center_ctl03_txtEmail_txt"
                            ).get_attribute("value")
                        )
                        other.add_phone(
                            self.driver.find_element(
                                By.ID, "ctl00_Center_ctl03_txtTelefono_txt"
                            ).get_attribute("value")
                        )
                        other.add_mobile_phone(
                            prefix=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl03_txtCodArea_Numerico"
                            ).get_attribute("value")
                            or "",
                            phone=self.driver.find_element(
                                By.ID, "ctl00_Center_ctl03_txtCel_Numerico"
                            ).get_attribute("value")
                            or "",
                        )
                        claim_data.add_other(other)
                        i += 1

                # END
                self.progress.set_completion("Done getting data.")
                if seclo_db_ok and not DEBUGMODE:
                    self.__save_claim_data()
                return claim_data
            except (
                NoSuchElementException,
                TimeoutException,
                StaleElementReferenceException,
            ) as e:
                attempts += 1
                last_exception = e
                logger.warning(e)
                continue
        raise AttemptsExceededException(last_exception)

    def get_conciliador_data(self: Self) -> str:
        """
        Returns the assigned conciliator for current case.
        """
        self.driver.get(
            f"https://conciliadores.trabajo.gob.ar/Conciliador_Reclamo.aspx?RecId={self.recid}"
        )
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "rcNroExpediente"))
        )
        try:
            return self.driver.find_element(By.ID, "rcConciliador").text
        except NoSuchElementException:
            return "UNKNOWN"

    def __complete_address_field(self: Self, field: WebElement, text: str) -> None:
        if not field.get_attribute("readOnly"):
            field.send_keys(text)
            WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "ui-widget-content"))
            )
            field.send_keys(Keys.ENTER + Keys.TAB)
            try:
                error_txt = (
                    WebDriverWait(self.driver, 1)
                    .until(
                        EC.visibility_of_element_located(
                            (By.CLASS_NAME, "divMensajeWarning")
                        )
                    )
                    .text
                )
                raise InvalidCaseStateException(f"Address error: {error_txt}")
            except (NoSuchElementException, TimeoutException):
                pass  # expected

    def add_employer(self: Self, employer: SECLOEmployerData) -> Self:
        """
        Attempts to expand a claim with the given employer.
        This can fail in many many ways, but we can try at least.
        Parameters:
            employer (SECLOEmployerData): The employer to be added.
        """
        self.progress.set_steps(1)
        self.progress.set_progress(0, "Loading claim data form...")

        for _ in range(0, 5):
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.ID, "ctl00_lnkModificacion"))
            ).click()
            self._load_rec()
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_ucReclamo_txtFecha"))
            )
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_lnkEmpleadores"))
            ).click()
            cuit_box = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_cuit_txtC"))
            )
            if cuit_box.is_enabled():
                break
            self.__save_claim_data()
        else:
            raise InvalidCaseStateException(
                "Couldn't open employer edit menu, you might need to edit this manually"
            )

        Select(
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_cmbTipoSociedad_cmb")
                )
            )
        ).select_by_value(str(
            employer.person_type.value[0] if employer.person_type is not None 
            else PersonType.PERSON.value[0]))
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_cuit_txtC"))
        ).send_keys(str(employer.cuil) + Keys.TAB)
        Select(
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_cmbActividad_cmb")
                )
            )
        ).select_by_value(
            "22"
        )  # Otra
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_txtActividad_txt"))
        ).send_keys("alguna actividad misteriosa de la cual desconocemos" + Keys.TAB)

        self.__complete_address_field(
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtProvincia")
                )
            ),
            employer.address.province if employer.address else "",
        )
        self.__complete_address_field(
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtPartido")
                )
            ),
            employer.address.district if employer.address else "",
        )
        self.__complete_address_field(
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtLocalidad")
                )
            ),
            employer.address.county if employer.address else "",
        )
        self.__complete_address_field(
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable(
                    (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtCalle")
                )
            ),
            employer.address.street if employer.address else "",
        )
        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtNumero")
            )
        ).send_keys(
            ((employer.address.number if employer.address else "") or "") + Keys.TAB
        )
        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtPiso")
            )
        ).send_keys((employer.address.floor if employer.address else "") or "")
        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtDepart")
            )
        ).send_keys((employer.address.apt if employer.address else "") or "")
        cpa = WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtCPA")
            )
        )
        if not cpa.get_attribute("value"):
            cpa.send_keys((employer.address.cpa if employer.address else "") or "")
        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable(
                (By.ID, "ctl00_Center_ctl01_Domicilio_direc_txtAdicional")
            )
        ).send_keys((employer.address.bonus_data if employer.address else "") or "")

        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_txtEmail_txt"))
        ).send_keys(employer.mail or "")
        WebDriverWait(self.driver, 1).until(
            EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_txtTelefono_txt"))
        ).send_keys(str(employer.phone) or "")

        if not DEBUGMODE:
            accept_button = WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_btnAgregar"))
            )
            accept_button.click()
            WebDriverWait(self.driver, 5).until(EC.staleness_of(accept_button))
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_ctl01_btnAgregar"))
            )
            error_text = self.driver.find_element(
                By.ID, "ctl00_Center_ctl01_ValidationSummary1"
            ).text.strip()
            if error_text:
                raise InvalidCaseStateException(error_text)
        return self


class SECLOInvoiceParser(SECLOAccessor):
    """
    A class for accessing invoices.
    Basically for nonagreements.
    """

    def list_invoices(self: Self) -> List[Dict[str, Any]]:
        """
        Fetches available list of invoices to be selected
        Returns:
            invoices: {'id': int, 'date': datetime}
        """
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_lnkConsultaLiquidacion"))
        ).click()
        invoices = []
        for option in (
            WebDriverWait(self.driver, 10)
            .until(EC.element_to_be_clickable((By.ID, "ctl00_Center_cmbLiquidaciones")))
            .find_elements(By.TAG_NAME, "option")
        ):
            invoices.append(
                {
                    "id": int(option.get_attribute("value") or 0),
                    "date": datetime.strptime(option.text.split()[0], "%d/%m/%Y"),
                }
            )
        return invoices

    def get_invoice_details(self: Self, invoice: int) -> Dict:
        """
        Fetches detailed info for given invoice ID.
        Returns:
            invoice: {
                'total': decimal,
                'details': [
                    'gdeID': str,
                    'description': str,
                    'amount': decimal,
                    'date': datetime
                ]
            }
        """
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "ctl00_lnkConsultaLiquidacion"))
        ).click()
        Select(
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Center_cmbLiquidaciones"))
            )
        ).select_by_value(str(invoice))
        self.driver.find_element(By.ID, "ctl00_Center_btnBuscar").click()

        result = []
        table = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "ctl00_Center_grdMovimientos"))
        )
        for row in table.find_elements(By.CLASS_NAME, "grdRowStyle"):
            result.append(
                {
                    "gdeID": row.find_elements(By.TAG_NAME, "td")[2].text,
                    "description": row.find_elements(By.TAG_NAME, "td")[3].text,
                    "amount": Decimal(
                        row.find_elements(By.TAG_NAME, "td")[4]
                        .text[2:-1]
                        .replace(".", "")
                        .replace(",", ".")
                    ),
                    "date": datetime.strptime(
                        row.find_elements(By.TAG_NAME, "td")[5].text, "%d/%m/%Y"
                    ),
                }
            )
        return {
            "total": Decimal(
                self.driver.find_element(By.ID, "ctl00_Center_lblTotal")
                .text.split()[1]
                .replace(",", ".")
            ),
            "detail": result,
        }


class SECLOCalendarParser(SECLOAccessor):
    """
    A class for accessing calendar info.
    Useful for registering newly assigned cases
    or verifying citation consistency.
    """

    def __iterate_calendar(self: Self, table: WebElement) -> List[int]:
        ids: List[int] = []
        # loop through days
        for day in (
            table.find_elements(By.TAG_NAME, "table")[1]
            .find_elements(By.TAG_NAME, "tr")[0]
            .find_elements(By.TAG_NAME, "td")
        ):
            # loop through cases in day
            for case in day.find_element(By.TAG_NAME, "div").find_elements(
                By.TAG_NAME, "div"
            ):
                aud_id = str(case.get_attribute("onclick"))
                if aud_id:
                    aud_id = re.search(r"PK:\d+", aud_id)
                    if aud_id:
                        ids.append(int(aud_id.group(0)[3:]))
        return ids

    def get_calendar(
        self: Self, weeks_before: int, weeks_after: int, date: Optional[datetime] = None
    ) -> List[SECLOCitation]:
        """
        Fetches the current calendar assignments from SECLO.
        Ideal entry point for claim registration and validating cases.
        Parameters:
            weeks_before (int): How many weeks before now to load.
            weeks_after (int): How many weeks after now to load.
            date (datetime): Override to load a specific week in absolute time.
        """
        first_stage = ProgressReport()
        second_stage = ProgressReport()
        (
            self.progress.compose(first_stage, "Parsing weeks").compose(
                second_stage, "Parsing citations"
            )
        )
        attempts = 0
        last_exception = None
        while attempts < MAX_ATTEMPTS:
            try:
                (
                    first_stage.set_steps(
                        1 + (1 if date else (weeks_before + weeks_after))
                    ).set_message("Loading calendar")
                )
                first_stage.set_progress(0, "Loading calendar")
                second_stage.set_steps(1)
                second_stage.set_progress(0, "")
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_btnAgenda"))
                ).click()

                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_Center_chkSusp"))
                ).click()
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_Center_chkReal"))
                ).click()

                ids = []
                # Loop through weeks
                if date:
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_Center_txtFecha_txt"))
                    ).send_keys(
                        Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + Keys.ARROW_LEFT
                        + date.strftime("%d/%m/%Y")
                    )
                    WebDriverWait(self.driver, 1).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_Center_btnConsultar"))
                    ).click()
                    first_stage.increase_progress(
                        f'Week of {date.strftime("%d/%m/%Y")}'
                    )
                    WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.ID, "ctl00_Center_DayPilotCalendar1")
                        )
                    )
                    table = self.driver.find_element(
                        By.ID, "ctl00_Center_DayPilotCalendar1"
                    ).find_element(By.TAG_NAME, "tr")
                    ids.extend(self.__iterate_calendar(table))
                else:
                    for i in range(0, weeks_after):
                        first_stage.increase_progress(
                            f"{i+1} of {weeks_before + weeks_after}"
                        )
                        WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.ID, "ctl00_Center_DayPilotCalendar1")
                            )
                        )
                        table = self.driver.find_element(
                            By.ID, "ctl00_Center_DayPilotCalendar1"
                        ).find_element(By.TAG_NAME, "tr")
                        ids.extend(self.__iterate_calendar(table))
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "ctl00_Center_lnkDer"))
                        ).click()
                    if weeks_before > 0:
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "ctl00_btnAgenda"))
                        ).click()

                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "ctl00_Center_chkSusp"))
                        ).click()
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "ctl00_Center_chkReal"))
                        ).click()
                        for i in range(0, weeks_before):
                            first_stage.increase_progress(
                                f"{i + weeks_after + 1} of {weeks_before + weeks_after}",
                            )
                            WebDriverWait(self.driver, 10).until(
                                EC.visibility_of_element_located(
                                    (By.ID, "ctl00_Center_DayPilotCalendar1")
                                )
                            )
                            table = self.driver.find_element(
                                By.ID, "ctl00_Center_DayPilotCalendar1"
                            ).find_element(By.TAG_NAME, "tr")
                            ids.extend(self.__iterate_calendar(table))
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable(
                                    (By.ID, "ctl00_Center_lnkIzq")
                                )
                            ).click()
                second_stage.set_steps(len(ids))
                second_stage.set_message("Loading citation data")
                first_stage.set_completion("Done")
                calendar_citations = []
                for index, item in enumerate(ids):
                    second_stage.increase_progress(f"{index + 1} of {len(ids)}")
                    self.driver.get(
                        "https://conciliadores.trabajo.gob.ar/Conciliador_Audiencia.aspx?"
                        + f"AudId={item}&esPortal=1"
                    )
                    gde_id_text = (
                        WebDriverWait(self.driver, 10)
                        .until(
                            EC.visibility_of_element_located((By.ID, "rcNroExpediente"))
                        )
                        .text
                    )
                    init_datetime_text = self.driver.find_element(By.ID, "rcFecha").text
                    init_datetime_text = (
                        init_datetime_text.split()[0]
                        + " "
                        + init_datetime_text.split()[1].split(":")[0]
                        + ":"
                        + init_datetime_text.split()[1].split(":")[1]
                    )
                    calendar_citations.append(
                        SECLOCitation(
                            gdeID=gde_id_text,
                            citationDate=datetime.strptime(
                                self.driver.find_element(By.ID, "rcFechaA").text.split(
                                    "a"
                                )[0],
                                r"%d/%m/%Y - %H:%M ",
                            ),
                            initDate=datetime.strptime(
                                init_datetime_text, r"%d/%m/%Y %H:%M"
                            ),
                            citationID=item,
                            citationType=self.driver.find_element(
                                By.ID, "auTipoYEstado"
                            ).text,
                            pdfString=self.driver.print_page(PRINT_OPTIONS),
                        )
                    )
                second_stage.set_completion("Done")
                return calendar_citations
            except (
                NoSuchElementException,
                TimeoutException,
                StaleElementReferenceException,
            ) as e:
                attempts += 1
                last_exception = e
                logger.warning(e, exc_info=True)
                continue
        raise AttemptsExceededException(last_exception)

    def get_workable_days(
        self: Self, weeks_ahead: int = 20
    ) -> List[Tuple[datetime, bool, str]]:
        """
        Fetches a list of workable and unworkable days.
        Useful for estimating notification periods.
        Parameters:
            weeks_ahead (int): How many weeks to load
        Returns:
            list: (day, isWorkable, description)
        """
        work_days: List[Tuple[datetime, bool, str]] = []
        self.progress.set_steps(weeks_ahead * 7)
        self.progress.set_message("Loading calendar info...")

        self.driver.get(
            "https://conciliadores.trabajo.gob.ar/pa_Abogados_Audiencias.aspx"
        )
        Select(
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Principal_CmbFormato"))
            )
        ).select_by_value(
            "1"
        )  # per-day
        for day in range(1, weeks_ahead * 7):
            cal = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.element_to_be_clickable(
                        (By.ID, "ctl00_Principal_DayPilotCalendar1")
                    )
                )
                .find_element(By.TAG_NAME, "tr")
                .find_elements(By.TAG_NAME, "table")[1]
            )
            date = datetime.strptime(
                str(
                    self.driver.find_element(
                        By.ID, "ctl00_Principal_txtFecha_txtFecha"
                    ).get_property("value")
                    or ""
                ),
                "%d/%m/%Y",
            )
            day = cal.find_elements(By.TAG_NAME, "tr")[2].find_element(
                By.TAG_NAME, "td"
            )
            day_title = (
                cal.find_elements(By.TAG_NAME, "tr")[1]
                .find_element(By.TAG_NAME, "td")
                .text
            )

            if "Feriado" in (day.get_attribute("title") or ""):
                work_days.append(
                    (
                        date,
                        False,
                        " ".join((day.get_attribute("title") or "").split()[1:]),
                    )
                )
            elif "dom" in day_title or "sáb" in day_title:
                work_days.append((date, False, day_title))
            else:
                work_days.append((date, True, ""))
            self.progress.increase_progress(
                f"Obtained info for {date.strftime('%d/%m/%Y')}"
            )
            self.driver.find_element(By.ID, "ctl00_Principal_lnkDer").click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(cal))
        self.progress.set_completion("Done getting cal info")
        return work_days


class SECLOClaimValidationData(SECLOAccessor):
    """
    Utility class for validating some data throuth a
    very rudimentary api provided by this website.

    Stuff like cuit, dni and addresses
    """

    def __create_request(self: Self, endpoint: str, data: str):
        cookies = {}
        cookie_list = self.driver.get_cookies()
        for cookie in cookie_list:
            cookies[cookie["name"]] = cookie["value"]
        ua = self.driver.execute_script("return navigator.userAgent")
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "es-419,es-US;q=0.9,es;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "conciliadores.trabajo.gob.ar",
            "Origin": "https://conciliadores.trabajo.gob.ar",
            "Refererer": "https://conciliadores.trabajo.gob.ar/ingresoreclamos.aspx",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": ua,
            "X-Requested-With": "XMLHttpRequest",
        }
        print(cookies)
        req = requests.Request(
            "POST", endpoint, data=data, headers=headers, cookies=cookies
        )
        req = req.prepare()
        print(
            "{}\n{}\r\n{}\r\n\r\n{}".format(
                "-----------START-----------",
                (req.method or "") + " " + (req.url or ""),
                "\r\n".join(f"{k}: {v}" for k, v in req.headers.items()),
                req.body,
            )
        )
        return requests.Session().send(req).json()

    def validate_cuit(self: Self, cuit: str):
        """
        Tries to validate the given CUIT.
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCuit.aspx/GetDatosCOmpletosxCuit",
            "{'dato': '" + cuit + "'}",
        )

    def validate_dni(self: Self, dni: str):
        """
        Tries to validate the given dni.
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioDocumento.aspx/getDatosxDenominacion",
            "{'dato': '" + dni + "', 'tipo': 'E'}",
        )

    def validate_district(self: Self, province: str, district: str):
        """
        Tries to validate the given district (for given province).
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetPartidos",
            "{'dato': '" + district + "', 'prov': '" + province + "'}",
        )

    def validate_county(self: Self, province: str, district: str, county: str):
        """
        Tries to validate the given county (for given province and district).
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetLocalidades",
            "{'dato': '"
            + county
            + "', 'prov': '"
            + province
            + "', 'part': '"
            + district
            + "'}",
        )

    def validate_street(
        self: Self, province: str, district: str, county: str, street: str
    ):
        """
        Tries to validate the given street (for given province, district and county).
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetCalles",
            "{'dato': '"
            + street
            + "', 'prov': '"
            + province
            + "', 'part': '"
            + district
            + "', 'localidad': '"
            + county
            + "'}",
        )

    def validate_cpa(
        self: Self, province: str, district: str, county: str, street: str, number: str
    ):
        """
        Tries to get the CPA (for given province, district, county, address and number.
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/getCPA",
            "{'prov': '"
            + province
            + "', 'part': '"
            + district
            + "', 'localidad': '"
            + county
            + "', 'calle': '"
            + street
            + "', 'numero': '"
            + number
            + "'}",
        )

    def get_street_helper(
        self: Self,
        province: str,
        street=str,
        district: Optional[str] = None,
        county: Optional[str] = None,
    ):
        """
        Tries to use street helper api to get possible places (?).
        """
        return self.__create_request(
            "https://conciliadores.trabajo.gob.ar/ServicioCPA.aspx/GetCallesHelper",
            "{"
            + f'\'prov\': \'{province}\', \'part\': \'{(district or "")}\', '
            + f'\'localidad\': \'{(county or "")}\', \'calle\': \'{street}\''
            + "}",
        )


if __name__ == "__main__":
    print("This script cannot be executed on its own")
