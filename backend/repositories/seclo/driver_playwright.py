"""
Module for interfacing with SECLO through their awful website.
Reimplemented in playwright for simplicity and async functionality.

This wretched thing basically frankensteins a chrome instance
and controls the website, manually loading and scraping data.
Manifest away those pesky Teams sharks.
"""

import asyncio
import base64
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Self, Set, Tuple
import uuid

# if __name__ == "__main__":
#     import sys

#     sys.path.append(str(Path.cwd()))
#     print(sys.path)

from dataobjects.enums import (
    ClaimType,
    PersonType,
    SECLOFileType,
    SECLONotificationType,
)
from dataobjects.seclodataclasses import (
    CitationResult,
    SECLOAddressData,
    SECLOCitation,
    SECLOClaimData,
    SECLOEmployeeData,
    SECLOEmployerData,
    SECLOLawyerData,
    SECLONotificationData,
    SECLOOtherData,
)
from repositories.seclo.driver import SECLOLoginCredentials
from repositories.seclo.progress import ProgressReport
from repositories.seclo.exceptions import (
    AttemptsExceededException,
    InvalidCaseStateException,
    InvalidParameterException,
    RecNotAccessibleException,
    UnauthorizedAccessException,
    UnknownReportedException,
    ValidationException,
)

from playwright.async_api import (
    APIRequestContext,
    APIResponse,
    Browser,
    Error as PlaywrightError,
    HttpCredentials,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    Route,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

logger = logging.getLogger(__name__)

PORTAL_VERSION_SUPPORTED = "8.5.6.0"
DEBUGMODE = os.getenv("DEBUGMODE", "TRUE") == "TRUE"
HEADLESS = os.getenv("HEADLESS", "TRUE") == "TRUE"
DOWNLOADROOT = os.getenv("TEMP_DOWNLOAD_PATH", "./temp")
MAX_ATTEMPTS = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "+\
             "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

def retry(func):
    "Decorator for auto retrying if errors occur"

    def myinner(*args, **kwargs):
        last_exception: PlaywrightError
        for _ in range(MAX_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except PlaywrightError as e:
                last_exception = e
                logger.debug(str(e))
        raise AttemptsExceededException() from last_exception  # type: ignore

    return myinner


class SECLOSession:
    """
    Handles creating a new browser instance for accessing the webportal.
    Done separate from the rest to be able to recycle instances with less overhead.

    Parameters:
        credentials (SECLOLoginCredentials): Credentials to use.
    """

    def __init__(
        self: Self,
        credentials: SECLOLoginCredentials,
    ):
        # Defining driver properties to avoid linting errors
        self.playwright: Playwright
        self.browser: Browser
        self.context: BrowserContext
        self.loginpage: Page
        # Actually setting properties
        self.credentials = credentials
        self.downloadpath = Path(f"{DOWNLOADROOT}/{uuid.uuid4()}")
        self.downloadpath = self.downloadpath.resolve()
        self.cache = {}
        os.mkdir(self.downloadpath)
        logger.debug("Download path set to %s", self.downloadpath)
        if DEBUGMODE:
            logger.warning(
                "WARNING! DEBUG mode enabled. Changes will not be submitted."
            )

    async def __proxy_req(self: Self, req: Route):
        if "trabajo" not in req.request.url:
            return await req.abort()
        if re.match(
            r".*(\.axd|\.js|\.css|\.gif|\.jpg|\.png)", req.request.url, re.IGNORECASE
        ):
            try:
                await req.fulfill(response=self.cache[req.request.url])
                return
            except KeyError as exc:
                headers = req.request.headers
                headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
                headers["Accept-Language"] = "es-419,es-US;q=0.9,es;q=0.8"
                headers["Cache-Control"] = "no-cache"
                headers["Connection"] = "keep-alive"
                headers["Dnt"] = "1"
                headers["Host"] = "conciliadores.trabajo.gob.ar"
                headers["Pragma"] = "no-cache"
                headers["sec-ch-ua-platform"] = "Windows"
                headers["sec-fetch-mode"] = "no-cors"
                headers["sec-fetch-site"] = "same-origin"
                headers["sec-Gpc"] = "1"
                ans: APIResponse
                last_exception: PlaywrightError
                for _ in range(MAX_ATTEMPTS):
                    try:
                        ans = await req.fetch(timeout=10000, headers=headers)
                        break
                    except PlaywrightError as ex:
                        last_exception = ex
                        continue
                else:
                    raise last_exception from exc  # type: ignore
                if ans.status == 200:
                    self.cache[ans.url] = ans
                await req.fulfill(response=ans)
                return
        return await req.fallback()

    async def __aenter__(self: Self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=HEADLESS, downloads_path=DOWNLOADROOT, timeout=60000
            )
            self.context = await self.browser.new_context(
                http_credentials=HttpCredentials(
                    username=self.credentials.user,
                    password=self.credentials.password,
                    send="unauthorized",
                ),
                user_agent=USER_AGENT,
                base_url="https://conciliadores.trabajo.gob.ar",
            )
            # await self.context.route("**/*", lambda req: req.fallback())
            await self.context.route("**/*", self.__proxy_req)
            await self.login()
            return self
        except PlaywrightError as e:
            await self.__aexit__(e.name, e, e.stack)
            raise e

    async def __aexit__(self: Self, exc_type, exc_val, exc_tb):
        if self.loginpage:
            await self.loginpage.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        os.rmdir(self.downloadpath)
        return False

    @retry
    async def login(self: Self):
        """Performs the auth procedure and logs into the web portal.
        Raises:
            UnauthorizedAccessException: If access was not granted.

        Returns:
            self
        """
        if hasattr(self, "loginpage") and self.loginpage:
            await self.loginpage.close()
        self.loginpage = await self.context.new_page()
        last_exc: Exception
        for _ in range(MAX_ATTEMPTS):
            logger.debug("Loading adfs")
            try:
                await self.loginpage.goto(
                    "https://login-int.trabajo.gob.ar/adfs/ls/wia"
                    + "?wa=wsignin1.0"
                    + "&wtrealm=https%3a%2f%2fconciliadores.trabajo.gob.ar%2f"
                    + "&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f"
                    + "&whr=https%3a%2f%2flogin-int.trabajo.gob.ar%2fadfs%2fservices%2ftrust"
                )
                break
            except PlaywrightError as e:
                last_exc = e
                logger.warning(str(e))
        else:
            raise AttemptsExceededException() from last_exc # type: ignore

        if "adfs" in self.loginpage.url:
            raise UnauthorizedAccessException(
                "Password is wrong or server entered inactive hours"
            )
        await self.loginpage.locator("#ctl00_Center_btnAceptar").click()
        logger.debug("Logged in.")
        try:
            await self.loginpage.locator(".ColCerrar").click(timeout=100)
            logger.debug("Closed notification panel.")
        except PlaywrightTimeoutError:
            logger.debug("Notification popup not found")

        logger.info(
            "Logged in as %s",
            await self.loginpage.locator("#ctl00_lblConciliador").inner_text(),
        )
        portal_version = await self.loginpage.locator(
            "#ctl00_LblAppVersion"
        ).inner_text()
        portal_version = portal_version.split()[1]

        if portal_version != PORTAL_VERSION_SUPPORTED:
            logger.warning(
                "Current portal version is %s, but driver supports up to %s. "
                + "Some features might be unexpectedly broken.",
                portal_version,
                PORTAL_VERSION_SUPPORTED,
            )
        else:
            logger.debug("Current portal version: %s", portal_version)
        return self


class SECLOAccessor:
    """
    Handles the access process to the webportal, including login and stuff.
    Other classes are meant to inherit from this.
    Provides some bullshit error handling as well, for when you get redirected to /Error.aspx.

    Parameters:
        session (SECLOSession): Playwright browser wrapper, to execute on.
        recid (Optional(int)): claim ID to bind accessor to.
            Optional, but if none, must later be populated.
        progress_report (Optional(ProgressReport)):
            an instance of ProgressReport to display progress for long calls.
    Returns:
        SECLOAccessor: Instance of SECLO webportal already logged in and ready for operations
    """

    def __init__(
        self: Self,
        session: SECLOSession,
        recid: Optional[int] = None,
        progress_report: Optional[ProgressReport] = None,
    ):
        self.session = session
        self.recid = recid
        self.progress = progress_report or ProgressReport()
        self.page: Page
        self.gde_id: str

    async def __aenter__(self: Self):
        self.page = await self.session.context.new_page()
        return self

    async def __aexit__(self: Self, exc_type, exc_val, exc_tb):
        await self.page.close()

    async def _error_handling(self):
        """
        Function to handle redirects to /Error.aspx page.
        There's not much to be done other than display some boilerplate error message.
        But if its an auth problem the caller could choose to try again,
        so we inform this using an exception.
        """
        try:
            if "Error.aspx" in self.page.url:
                error = await self.page.locator("#lblError").inner_text(timeout=100)
                if "No tiene permisos para acceder" in error:
                    raise UnauthorizedAccessException(
                        "SECLO Authorization error. "
                        + "Try initiating the request again, the token probably expired."
                    )
                if "ha caducado" in error:
                    raise UnauthorizedAccessException("Session expired, log in again")
        except PlaywrightTimeoutError:
            pass
        raise UnknownReportedException(
            "Unknown SECLO server error. Try initiating the request again."
        )

    @retry
    async def _load_rec(self: Self):
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
            await self.page.wait_for_load_state(timeout=60000)
            await self.page.evaluate(
                'document.getElementById("ctl00_Top_hdnReclamoId")'+\
                f'.setAttribute("value", "{self.recid}")'
            )

            # await self.page.locator("#ctl00_Top_hdnReclamoId").fill(
            #     str(self.recid), force=True
            # )
            await self.page.locator("#ctl00_Busqueda_btnBuscar").click(timeout=60000)
        except PlaywrightTimeoutError as e:
            logger.error(e)
            raise RecNotAccessibleException(
                "Couldn't find case searchbox element"
            ) from e

    @retry
    async def set_rec_id_from_gde_id(self: Self, gde_id: str) -> Self:
        """
        Sets the current RecID to the corresponding key for the given gdeID.

        Parameters:
            gde_id (str): The given gde ID to find a case. eg: "EX-2020-00000000-bullshit"
        """

        self.progress.set_steps(1)
        await self.progress.set_progress(0, "Setting recID")
        logger.debug("Setting recID from gdeID %s", gde_id)
        await self.page.goto(
            "/O_ConsultaNotificaciones.aspx", timeout=60000
        )

        gde_year = gde_id.split("-")[1]
        gde_file = gde_id.split("-")[2]
        logger.debug("gde year: %s", gde_year)
        logger.debug("gde file: %s", gde_file)
        await self.page.locator("#ctl00_Busqueda_txtNro").fill("")
        await self.page.locator("#ctl00_Busqueda_txtNro").fill(gde_file)
        await self.page.locator("#ctl00_Busqueda_txtAnio").fill("")
        await self.page.locator("#ctl00_Busqueda_txtAnio").fill(gde_year)
        await self.page.locator("#ctl00_Busqueda_btnBuscar").click()
        try:
            await self.page.locator("#ctl00_Center_grdNotificaciones").is_visible(
                timeout=10000
            )
        except PlaywrightTimeoutError as e:
            raise RecNotAccessibleException(
                f"Case with GDE ID '{gde_id}' not found"
            ) from e
        rec_id = await self.page.locator("#ctl00_Top_hdnReclamoId").get_attribute(
            "value"
        )
        if rec_id:
            self.recid = int(rec_id)
        else:
            raise RecNotAccessibleException(f"Can't load recID for {gde_id}. bummers")
        await self.progress.set_completion("Done")
        logger.info("recID found, set to %s", self.recid)
        return self

    @retry
    async def set_gde_id_from_rec_id(self: Self, rec_id: int) -> Self:
        """
        Sets the corresponding GDE ID for a given case.
        Parameters:
            rec_id (int): The recID to set a GDEID from
        Returns:
            Self: self
        """
        await self.page.goto(
            f"/Conciliador_Reclamo.aspx?RecId={rec_id}"
        )
        try:
            self.gde_id = await self.page.locator("#rcNroExpediente").inner_text(
                timeout=100
            )
        except PlaywrightTimeoutError as e:
            logger.error("Case not found")
            raise RecNotAccessibleException() from e
        return self

    def set_progress(self: Self, progress: ProgressReport) -> Self:
        """
        Sets a progress reporter for this driver instance.
        Parameters:
            progress (ProgressReport): The progressReport object to override current.
        Returns:
            Self: self
        """
        self.progress = progress
        return self

    def set_rec_id(self: Self, rec_id: int) -> Self:
        """
        Manually sets this driver's recID.
        Parameters:
            rec_id (int): The recID to use.
        Returns:
            Self: self
        """
        self.recid = rec_id
        return self

    async def _save_standard(self: Self, save_button: Locator):
        await save_button.click()
        await self.page.locator("#ctl00_Center_TRGRABANDO").wait_for(
            timeout=100, state="visible"
        )
        await self.page.locator("#ctl00_Center_TRGRABANDO").wait_for(
            timeout=20000, state="hidden"
        )


class SECLOCitationManager(SECLOAccessor):
    """
    A browser driver class to register citation results on the SECLO site.
    Used for creating a new citation or closing a case with or without agreement.
    Most methods return self for easy chaining.
    eg. citation= SECLOCitation().setRecIDfromGDEID().reopenCase().getItems()
        citation.closeCase()
        citation.createNewCitation()

    Parameters:
        session (SECLOLoginCredentials): The session to use for the requests.
        rec_id (Optional(int)): The recID to set for this instance.
        date (datetime): The presentation date to set for the result form. Current date by default.
        progress: Instance of ProgressReport to report progress on blocking functions.
    """

    def __init__(
        self,
        session: SECLOSession,
        recid: Optional[int] = None,
        date: Optional[datetime] = None,
        progress: Optional[ProgressReport] = None,
    ):
        super().__init__(session, recid, progress_report=progress)
        self.date = date or datetime.now()
        self.error = None
        self.multiple = False
        self.comb_selector_length = 0
        self.comb_selector_index = 0
        self.items: List[CitationResult] = []

    @retry
    async def __load_citation_result_screen(self: Self) -> None:
        """
        Loads the first screen of the result form (aka selecting agreement/non-agreement)
        """
        logger.debug("Accessing citation result window")
        await self.page.goto(
            "/O_Audiencia.aspx?paramEnc=XNxZmSrDl/0vB4gXlCNe3A=="
        )
        await self.page.locator("#ctl00_btnAudiencia").click()
        await self._load_rec()
        try:
            if (
                "Registrar Resultado"
                in await self.page.locator(".appBoxMenu").inner_text()
            ):
                if not await self.page.locator("#ctl00_Center_cmbObjetos").is_enabled():
                    logger.debug(
                        "Claim object comb selector is disabled. This is good."
                    )
                    self.multiple = False
                    self.comb_selector_length = 1
                else:
                    logger.debug(
                        "Claim object comb selector is enabled. This will be a bummer"
                    )
                    self.multiple = True
                    self.comb_selector_length = (
                        await self.page.locator("#ctl00_Center_cmbObjetos")
                        .locator("option")
                        .count()
                    )
                    self.comb_selector_index = 0
        except Exception as e:
            raise RecNotAccessibleException(
                f"Could not access result form for rec {self.recid}. Maybe its closed."
            ) from e

    @retry
    async def reopen_case(self: Self) -> Self:
        """
        Reopens a given case. Does not verify if its closed, thats the responsibility of the caller.
        Returns:
            Self:
        """
        logger.debug("Attempting to reopen case %s", str(self.recid))
        self.progress.set_steps(2)
        await self.progress.set_progress(0, "Loading case for reopening")

        try:
            await self.page.goto("/O_Reabrir_Reclamo.aspx")
            await self._load_rec()
            await self.progress.increase_progress("Reopening case")
            # if present, case was not found
            await self.page.wait_for_load_state("load")
            await self.page.locator("#ctl00_Busqueda_grdReclamos").is_visible(
                timeout=100
            )
        except PlaywrightTimeoutError:
            pass  # Expected
        else:
            raise InvalidCaseStateException("Case not found, probably its still open")

        logger.debug("Reopen found")
        try:
            # if present, an error was raised
            error = await self.page.locator("#ctl00_Center_lblmensaje").inner_text(
                timeout=100
            )
        except PlaywrightTimeoutError:
            pass  # expected
        else:
            if error:
                raise InvalidCaseStateException(error)
        if not DEBUGMODE:
            await self.page.locator("#ctl00_Center_btnReabrir").click()
        else:
            logger.warning("DEBUG MODE WON'T SUBMIT REOPENING REQUEST")
        await self.progress.set_completion("Done reopening")
        return self

    async def __row_to_result(
        self: Self, row: Locator, is_employee: bool = True
    ) -> CitationResult:
        if is_employee:
            try:
                enabled = (
                    await row.locator("td")
                    .nth(2)
                    .locator("td")
                    .first.is_enabled(timeout=100)
                )
            except PlaywrightTimeoutError:
                logger.warning(
                    "Could not access properties for agreement selector switch."
                )
                enabled = True
            amount = (
                await row.locator("td").nth(4).locator("input").input_value()
            ).lstrip()
            logger.debug('Amount string "%s"', amount)
            if len(amount) == 0 or amount == 0:
                amount = None
            person = await row.locator("td").first.inner_text()
        else:
            amount = None
            enabled = False
            person = await row.locator("td").nth(1).inner_text()
        return CitationResult(
            person=person, amount=amount, enabled=enabled, is_employee=is_employee
        )

    @retry
    async def get_items(self: Self) -> List[CitationResult]:
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
        await self.progress.set_progress(0, "Loading case")
        await self.__load_citation_result_screen()
        fields = []
        fields_len = 0
        logger.debug("Case attained")

        await self.progress.increase_progress("Loading items")
        try:
            table = self.page.locator("#ctl00_Center_grdAcuerdos_grdAcuerdos")
            for row in await table.locator(".grdRowStyle").all():
                fields.append(await self.__row_to_result(row, True))
                fields.append(await self.__row_to_result(row, False))
                fields_len += 1
            fields = set(fields)
            await self.progress.set_completion("Done getting items.")
            return list(fields)
        except Exception as e:
            raise InvalidCaseStateException(
                "Something bad happenned loading the results."
            ) from e

    async def __row_populated_check(self: Self, row: Locator) -> bool:
        """
        Checks whether a row from citation result screen is populated already.

        Parameters:
            row (Locator): A table row selected from the result screen
        Returns:
            bool: Whether the row is populated or not
        """
        return (
            await row.locator("td")
            .nth(2)
            .locator("td")
            .nth(1)
            .locator("input")
            .is_checked()
            or await row.locator("td")
            .nth(2)
            .locator("td")
            .nth(0)
            .locator("input")
            .is_checked()
        )

    async def __get_matching_rows(
        self, entry: CitationResult
    ) -> List[Tuple[int, Locator]]:
        """
        For a given entry, finds all matching rows.
        Parameters:
            entry (CitationResult): Entry to search for. Can only be employee.
        Returns:
            list: A list containing a (idx, Locator) tuple for every row matched
        """
        rows = []
        logger.info("Getting table contents")
        table = self.page.locator("#ctl00_Center_grdAcuerdos_grdAcuerdos")

        for i, row in enumerate(await table.locator(".grdRowStyle").all()):
            result = await self.__row_to_result(row, True)
            # check if matches
            if (
                result == entry
                and not await self.__row_populated_check(row)
                and entry.enabled
                and result.enabled
            ):
                rows.append((i, row))
        return rows

    async def __set_item(self: Self, entry: CitationResult):
        loop = True
        # TODO better algo
        while loop:
            loop = False
            rows = await self.__get_matching_rows(entry)
            await self.progress.increase_progress("Setting results...")
            for i, row in rows:
                logger.debug("Row %d matches %s and is unselected, applying", i, entry)
                if entry.amount:
                    # Set agreement
                    logger.info("Agreement for %s", entry)
                    await row.locator("td").nth(2).get_by_text("Sí").set_checked(True)
                    # Flag so we iterate again, there may be another row for employee
                    # Yes, this site sucks, i'm well aware of that, even moreso by now
                    loop = True

                    # Matches, so populate amount
                    await row.locator("input[type=text]").fill("")
                    await row.locator("input[type=text]").fill(
                        entry.amount.replace(".", ",")
                    )
                else:
                    # set non-agreement
                    logger.info("Non-agreement for %s", entry)
                    await row.locator("td").nth(2).get_by_text("No").set_checked(True)
                    loop = True

    async def __set_items(self: Self, ignore_multiple_comb: bool = False) -> Self:
        logger.info("Performing Citation getItems")
        await self.__load_citation_result_screen()

        if self.multiple:
            if (
                self.comb_selector_index == self.comb_selector_length
                or ignore_multiple_comb
            ):
                logger.debug("Done setting items.")
                return await self.__advance_result_form()
            await self.page.locator("#ctl00_Center_cmbObjetos").select_option(
                index=self.comb_selector_index
            )
            logger.debug(
                "Selected comb level entry %d of %d",
                self.comb_selector_index + 1,
                self.comb_selector_length,
            )
            self.comb_selector_index += 1
        self.progress.set_steps(1 + self.comb_selector_length * (len(self.items) + 1))
        try:
            for entry in set(self.items):
                if entry.is_employee:
                    await self.__set_item(entry)
        except PlaywrightTimeoutError:
            await self._error_handling()
        for row in await (
            self.page.locator("#ctl00_Center_grdAcuerdos_grdAcuerdos")
            .locator(".grdRowStyle")
            .all()
        ):
            if not await self.__row_populated_check(row):
                raise InvalidCaseStateException("Incomplete selection")
        return await self.__advance_result_form()

    async def __fill_date_input(self: Self, input_id: str, date: datetime):
        logger.info(self.date.strftime("%d%m%Y"))
        await self.page.locator(f"#{input_id}").fill("")
        await self.page.locator(f"#{input_id}").fill(date.strftime("%d%m%Y"))

    async def __advance_result_form(self: Self):
        try:
            await self.__fill_date_input("ctl00_Center_txtFecha_txtFecha", self.date)
            await self.page.locator("#ctl00_Center_btnSeguir4").click(timeout=1000)
        except PlaywrightTimeoutError as e:
            raise InvalidCaseStateException("Error submitting form") from e
        await self.__validation_error_checker()
        return self

    async def __validation_error_checker(self: Self):
        try:
            self.error = await self.page.locator("#ctl00_Center_lblError").inner_text(
                timeout=100
            )
        except PlaywrightTimeoutError:
            pass  # Expected, means no errors
        else:
            raise ValidationException(self.error)

        try:
            self.error = await self.page.locator(
                "#ctl00_Center_ValidationSummary5"
            ).inner_text(timeout=100)
        except PlaywrightTimeoutError:
            pass  # Expected, means no errors
        else:
            raise ValidationException(self.error)

    @retry
    async def create_new_citation(
        self: Self, items: Set[CitationResult], date: datetime
    ):
        """
        Receives a modified items set with the appropiate result
        and notification data, plus a date, and registers a new citation.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (Set[CitationResult]): The set provided by getItems with attributes set.
            date: The date and time requested for the new citation.
        """
        self.items = list(items)
        await self.__set_items(True)
        absent_citation = False
        await self.progress.increase_progress("Setting new citation date")
        for item in self.items:
            if item.absent:
                absent_citation = True
        if absent_citation:
            await self._save_standard(
                self.page.locator("#ctl00_Center_btnNuevaIncomparecencia")
            )
        else:
            await self._save_standard(
                self.page.locator("#ctl00_Center_btnNuevaAudiencia")
            )
        await self.__fill_date_input("ctl00_Center_txtFecha_txtFecha", date)

        await self.page.locator("#ctl00_Center_cmbHoras").select_option(
            label=f"{date.hour:02}"
        )
        await self.page.locator("#ctl00_Center_cmbMinutos").select_option(
            f"{(date.minute - date.minute % 5):02}"
        )

        for row in await (
            self.page.locator("#ctl00_Center_grdTrabajadores")
            .locator(".grdRowStyle")
            .all()
        ):
            for entry in self.items:
                if (
                    await row.locator("td").nth(0).inner_text() in entry.get_person()
                    and await row.locator("td").nth(1).inner_text()
                    in entry.get_person()
                ):
                    if entry.absent:
                        await row.locator("td").nth(2).locator("input").click()
                    if entry.notify:
                        if absent_citation:
                            await row.locator("td").nth(3).locator("input").click()
                    await row.locator("select").select_option(
                        value=entry.notif_method.value
                    )
                    break

        for row in await (
            self.page.locator("#ctl00_Center_grdEmpleadores")
            .locator(".grdRowStyle")
            .all()
        ):
            for entry in self.items:
                if await row.locator("td").nth(0).inner_text() in entry.get_person():
                    if entry.absent:
                        await row.locator("td").nth(1).locator("input").click()
                    if entry.notify:
                        if absent_citation:
                            await row.locator("td").nth(2).locator("input").click()
                    await row.locator("select").select_option(
                        value=entry.notif_method.value
                    )

        if not DEBUGMODE:
            await self._save_standard(self.page.locator("#ctl00_Center_btnGrabar"))
            await self.__validation_error_checker()
        else:
            logger.warning(
                "DEBUG MODE WON'T PERSIST NEW CITATION. "
                + "However, this citation will be 'completed' rather than 'pending'"
            )
        await self.progress.set_completion("Done new citation request")

    @retry
    async def close_case(self: Self, items: set[CitationResult]):
        """
        Sets the claim results based on the items and then closes the case.
        This method will render this instance useless, as it will destroy the webdriver.
        Parameters:
            items (set[CitationResult]): The modified set provided by getItems with results set.
        """
        self.items = list(items)
        if self.multiple:
            while self.comb_selector_index < self.comb_selector_length:
                await self.__set_items(False)
                await self.progress.increase_progress("Closing partial claim")
        else:
            await self.__set_items(False)
            await self.progress.increase_progress("Closing claim")

        if not DEBUGMODE:
            await self._save_standard(self.page.locator("#ctl00_Center_btnGrabarTotal"))

        else:
            logger.warning("DEBUG MODE WON'T SUBMIT CLOSE REQUEST.")
        await self.progress.set_completion("Done closing claim")


class SECLOFileManager(SECLOAccessor):
    """
    A class to handle file management,
    including querying and downloading already present files,
    uploading new ones, or uploading records.

    Parameters:
        session (SECLOSession): The SECLO session used to process these commands.
        recid (int): Tha claim number to bind to this instance.
    """

    def __init__(self: Self, session: SECLOSession, recid: Optional[int] = None):
        super().__init__(session, recid)
        self.file_list: List[Tuple[str, str, datetime]] = []

    async def __aenter__(self: Self) -> Self:
        await super().__aenter__()
        await self.__get_files()
        return self

    @retry
    async def __get_files(self: Self):
        """
        Populates internal object storage with the current files in rec.
        idc about congruency, this is a throwaway object that expires quickly.
        """
        await self.page.goto(f"Documentacion_Adjunta.aspx?RecId={self.recid}")
        files: List[Tuple[str, str, datetime]] = []
        for row in (
            await self.page.locator("#grdDocumentos").locator(".grdRowStyle").all()
        ):
            files.append(
                (
                    await row.locator("td").first.inner_text(),
                    await row.locator("td").nth(1).inner_text(),
                    self.__shit_date_to_datetime(
                        await row.locator("td").nth(2).inner_text()
                    ),
                )
            )
            logger.debug(files[-1])
        self.file_list = files
        return files

    def get_files(self: Self) -> List[Tuple[str, str, datetime]]:
        """
        Gets a list of all the registered files currently uploaded to this rec.

        Returns:
            files (Tuple[str, str, datetime]): (type, description, date)
        """
        return self.file_list[:]

    @retry
    async def get_file(self: Self, index: int) -> Path:
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
        logger.debug("Downloading file")
        download_button = (
            self.page.locator("#grdDocumentos")
            .locator(".grdRowStyle")
            .nth(index)
            .locator("input[type=image]")
        )
        download_path = self.session.downloadpath / "TEST.pdf"
        logger.info(await download_button.get_attribute("title"))
        download_event = self.page.wait_for_event("download")
        await download_button.click()
        await (await download_event).save_as(download_path)
        return download_path

    @retry
    async def upload_file(
        self: Self,
        file: str,
        filetype: SECLOFileType,
        description: Optional[str] = None,
    ) -> None:
        """
        Uploads a file. Works for everything except records,
        which are uploaded using the upload_record method because
        it's completely different for some godforsaken reason.
        Parameters:
            file (str): The path to the file to be uploaded. Must be a PDF.
            filetype: The given filetype to upload, from the enum.
            description: Only used when uploading a 'other' type of file.
        """
        await self.page.goto(f"/Documentacion_ParaAdjuntar.aspx?RecId={self.recid}")
        old_files_len = len(self.file_list)
        await self.page.locator("#Tipo_Documentacion").select_option(
            value=filetype.value[0]
        )
        if filetype.value[1]:
            if description is None:
                raise InvalidParameterException(
                    "Description cannot be null for this type of file"
                )
            await self.page.locator("#txtDescripcion").fill(description)
        await self.page.locator("#Archivo").set_input_files(file)
        await self.page.locator("#btnAgregar").click()
        await self.__get_files()

        if old_files_len == len(self.file_list):
            raise InvalidCaseStateException("File was not uploaded")

        if not DEBUGMODE:
            await self.page.locator("#Button1").click()
            await self.page.wait_for_event("response")
            error_str = (
                await self.page.locator(".ingreso").locator("tr").nth(1).inner_text()
            )
            error_str = error_str.strip()
            if error_str:
                raise ValidationException(f"Error uploading file: {error_str}")
        else:
            logger.warning("FILE WON'T BE SAVED IN DEBUG MODE!")
        await self.__get_files()

    @retry
    async def upload_record(
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
                await self.set_gde_id_from_rec_id(self.recid)
            else:
                raise InvalidParameterException("Missing recID and gdeID")
        logger.info(self.gde_id)

        await self.page.goto("/Novedades.aspx")
        await self.page.locator("#ctl00_btnActa").click()
        if agreement:
            await self.page.locator("#ctl00_Center_radTipo_0").set_checked(True)
        else:
            await self.page.locator("#ctl00_Center_radTipo_1").set_checked(True)
        await self.page.locator("#ctl00_Center_btnBuscar").click()

        table = self.page.locator("#ctl00_Center_grdReclamos")
        if await table.locator(".grdEmptyStyle").is_visible():
            raise InvalidCaseStateException(
                "There are no elements available to upload records here. That sucks, man."
            )
        row = table.locator(".grdRowStyle", has_text=self.gde_id)
        if await row.is_visible():
            if await row.locator("input[type=image]").is_visible():
                logger.warning(
                    "Claim %s already has record uploaded (%s)",
                    self.gde_id,
                    "agreement" if agreement else "nonagreement",
                )
                if not override:
                    return
            await row.locator("input[type=file]").set_input_files(file)
        else:
            raise InvalidCaseStateException(
                "Given claim does not have record uploading enabled right now."
            )

        if not DEBUGMODE:
            await self.page.locator("#ctl00_Center_btnGenerar").click()
            await self.page.locator("#ctl00_Center_grdReclamos").is_visible()

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

    @retry
    async def get_notification_data(
        self: Self, gde_id: Optional[str] = None, rec_id: Optional[int] = None
    ) -> List[SECLONotificationData]:
        """
        Gets the associated notification information for a given case.
        Its up to the caller to link those to a citation or stuff like that.

        Returns:
            List[SECLONotificationData]: The list of notification entries.
        """

        if gde_id:
            await self.set_rec_id_from_gde_id(gde_id=gde_id)
        else:
            if rec_id:
                self.recid = rec_id
            await self.page.goto("O_ConsultaNotificaciones.aspx", timeout=60000)
            await self._load_rec()

        self.progress.set_steps(1)

        results = []
        table = self.page.locator("#ctl00_Center_grdNotificaciones")
        for row in await table.locator(".grdRowStyle").all():
            results.append(
                SECLONotificationData(
                    id=int(await row.locator("td").nth(0).inner_text()),
                    person=await row.locator("td").nth(1).inner_text(),
                    citationType=await row.locator("td").nth(2).inner_text(),
                    isEmployer=await row.locator("td").nth(3).inner_text() == "Emp",
                    notificationType=SECLONotificationType.notification_short_to_enum(
                        await row.locator("td").nth(4).inner_text()
                    ),
                    generatedDate=datetime.strptime(
                        await row.locator("td").nth(5).inner_text(), "%d/%m/%Y"
                    ),
                    notifiedDate=(
                        None
                        if not await row.locator("td").nth(6).inner_text()
                        else datetime.strptime(
                            await row.locator("td").nth(6).inner_text(), "%d-%m-%Y"
                        )
                    ),
                    notificationCode=await row.locator("td").nth(7).inner_text(),
                    notificationStatus=await row.locator("td").nth(8).inner_text(),
                    afipRead="S" in await row.locator("td").nth(9).inner_text(),
                    citationDate=datetime.strptime(
                        await row.locator("td").nth(10).inner_text(), "%d/%m/%Y %H:%M"
                    ),
                    citationStatus=await row.locator("td").nth(11).inner_text(),
                )
            )

        await self.progress.set_completion(f"Found notif data for {self.recid}")
        return results

    async def __save_claim_data(self: Self):
        await self.page.locator("#ctl00_Center_lnkFinalizar").click()
        await self.page.locator("#ctl00_Center_btnAceptarRec").click()
        await self.page.wait_for_load_state()
        if await self.page.locator("#ctl00_Center_btnSi").is_visible():
            await self.page.locator("#ctl00_Center_btnSi").click()

    async def __get_address(self: Self, tab: int = 0) -> SECLOAddressData:
        return SECLOAddressData(
            province=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtProvincia"
            ).input_value(),
            district=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtPartido"
            ).input_value(),
            county=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtLocalidad"
            ).input_value(),
            street=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtCalle"
            ).input_value(),
            number=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtNumero"
            ).input_value(),
            floor=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtPiso"
            ).input_value(),
            apt=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtDepart"
            ).input_value(),
            cpa=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtCPA"
            ).input_value(),
            bonus_data=await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_Domicilio_direc_txtAdicional"
            ).input_value(),
        )

    async def __get_email(self: Self, tab: int = 0) -> str:
        return (
            await self.page.locator(
                f"#ctl00_Center_ctl0{tab}_txtEmail_txt"
            ).input_value()
        ).strip()

    async def __get_phone(self: Self, tab: int = 0) -> str:
        return await self.page.locator(
            f"#ctl00_Center_ctl0{tab}_txtTelefono_txt"
        ).input_value()

    async def __get_mobile_phone(self: Self, tab: int = 0) -> tuple[str, str]:
        prefix = await self.page.locator(
            f"#ctl00_Center_ctl0{tab}_txtCodArea_Numerico"
        ).input_value()
        phone = await self.page.locator(
            f"#ctl00_Center_ctl0{tab}_txtCel_Numerico"
        ).input_value()
        return prefix, phone

    async def __get_employee_data(
        self: Self, seclo_db_ok: bool
    ) -> tuple[SECLOEmployeeData, bool]:
        cuil = self.page.locator("#ctl00_Center_ctl00_cuit_txtC")
        name = f'{await self.page
                    .locator("#ctl00_Center_ctl00_txtApellido_txt").input_value()
                } {await self.page
                    .locator("#ctl00_Center_ctl00_txtNombre_txt").input_value()
                }'

        if await cuil.input_value() and seclo_db_ok and await cuil.is_enabled():
            await cuil.click()
            await cuil.press("Tab")
            await expect(
                self.page.locator("#ctl00_Center_ctl00_cuit_txtRS")
            ).to_have_value(re.compile(".+", re.IGNORECASE), timeout=30000)
            validated_name = await self.page.locator(
                "#ctl00_Center_ctl00_cuit_txtRS"
            ).input_value()
            if "null null" in validated_name:
                seclo_db_ok = False
            else:
                name = validated_name

        employee = SECLOEmployeeData(
            name=name,
            dni=await self.page.locator(
                "#ctl00_Center_ctl00_txtNroDocumentoComplete_txtRS"
            ).input_value(),
            cuil=(await cuil.input_value()).replace("-", ""),
            validated=seclo_db_ok,
        )
        employee.add_address(await self.__get_address(0))
        employee.add_birth_date(
            await self.page.locator(
                "#ctl00_Center_ctl00_txtFecNacimiento_txt"
            ).input_value()
        )
        employee.add_claim_amount(
            await self.page.locator("#ctl00_Center_ctl00_txtImporte_txt").input_value()
        )
        employee.add_mail(await self.__get_email(0))
        employee.add_mobile_phone(*await self.__get_mobile_phone(0))
        employee.add_phone(await self.__get_phone(0))
        employee.add_start_date(
            await self.page.locator(
                "#ctl00_Center_ctl00_txtFecIngreso_txt"
            ).input_value()
        )
        employee.add_end_date(
            await self.page.locator(
                "#ctl00_Center_ctl00_txtFecEgreso_txt"
            ).input_value()
        )
        employee.add_type(
            cct=await self.page.locator(
                "#ctl00_Center_ctl00_txtConvenioNum_txt"
            ).input_value(),
            category=await self.page.locator(
                "#ctl00_Center_ctl00_txtCategoria_txt"
            ).input_value(),
        )
        employee.add_wage(
            await self.page.locator(
                "#ctl00_Center_ctl00_txtRemuneracion_txt"
            ).input_value()
        )
        return employee, seclo_db_ok

    async def __get_employer_data(
        self: Self, seclo_db_ok: bool
    ) -> tuple[SECLOEmployerData, bool]:
        await expect(self.page.locator("#ctl00_Center_ctl01_cuit_txtRS")).to_have_value(
            re.compile(".+", re.IGNORECASE), timeout=30000
        )
        name = (
            await self.page.locator("#ctl00_Center_ctl01_cuit_txtRS").input_value()
        ).replace('"', "")
        if "null null" in name:
            seclo_db_ok = False
        cuil = (
            await self.page.locator("#ctl00_Center_ctl01_cuit_txtC").input_value()
        ).replace("-", "")
        dni = await self.page.locator(
            "#ctl00_Center_ctl01_txtNroDocumento_txt"
        ).input_value()
        employer = SECLOEmployerData(
            name=name,
            dni=dni,
            cuil=cuil,
            validated=seclo_db_ok and len(cuil) > 0,
        )
        employer.add_address(await self.__get_address(1))
        employer.add_mail(await self.__get_email(1))
        for item in (
            await self.page.locator("#ctl00_Center_ctl01_cmbTipoSociedad_cmb")
            .locator("option")
            .all()
        ):
            if await item.get_attribute("selected"):
                employer.add_person_type(
                    PersonType.from_string(await item.inner_text())
                )
                break
        employer.add_phone(await self.__get_phone(1))
        return employer, seclo_db_ok

    async def __get_lawyer_data(self: Self, seclo_db_ok: bool) -> SECLOLawyerData:
        email = await self.__get_email(2)
        phone = await self.__get_phone(2)
        mobilephone = await self.__get_mobile_phone(2)

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
                await self.page.locator(
                    "#ctl00_Center_ctl02_txtNombre_lbl"
                ).inner_text(),
                await self.page.locator(
                    "#ctl00_Center_ctl02_txtApellido_lbl"
                ).inner_text(),
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

        lawyer = SECLOLawyerData(
            name=name,
            dni=await self.page.locator(
                "#ctl00_Center_ctl02_txtNroDocumento_lbl"
            ).inner_text(),
            validated=seclo_db_ok and self_validated,
        )
        lawyer.add_address(await self.__get_address(2))

        for row in (
            await self.page.locator("#ctl00_Center_ctl02_lstAsignados")
            .locator("td")
            .all()
        ):
            if await row.locator("input").is_checked():
                name = (await row.inner_text()).replace(",", "")
                lawyer.add_represented(
                    is_employee=await self.page.locator(
                        "#ctl00_Center_ctl02_chkRepresentantes_0"
                    ).is_checked(),
                    name=name,
                )
        lawyer.add_phone(phone)
        lawyer.add_mobile_phone(*mobilephone)
        lawyer.add_mail(email)
        lawyer.add_tf(
            t=await self.page.locator("#ctl00_Center_ctl02_txtTomo_txt").input_value(),
            f=await self.page.locator("#ctl00_Center_ctl02_txtFolio_txt").input_value(),
        )
        return lawyer

    async def __get_other_data(self: Self) -> SECLOOtherData:
        name = " ".join(
            [
                await self.page.locator(
                    "#ctl00_Center_ctl03_txtApellido_txt"
                ).input_value(),
                await self.page.locator(
                    "#ctl00_Center_ctl03_txtNombre_txt"
                ).input_value(),
            ]
        )
        dni = await self.page.locator(
            "#ctl00_Center_ctl03_txtNroDocumento_txt"
        ).input_value()
        other = SECLOOtherData(name=name, dni=dni)
        other.add_address(await self.__get_address(3))
        other.add_mail(await self.__get_email(3))
        other.add_phone(await self.__get_phone(3))
        other.add_mobile_phone(*await self.__get_mobile_phone(3))
        return other

    @retry
    async def get_claim_data(self: Self) -> SECLOClaimData:
        """
        Accesses the given claims initiation data.
        Useful to get names, IDs, employment parameters, etc.

        Returns:
            SECLOClaimData: an object that contains all claim data.
        """
        self.progress.set_steps(1)
        await self.progress.set_progress(0, "Loading claim data form...")
        await self.page.goto(
            "/ingresoreclamos.aspx?paramEnc=AB3u3y2175MqNXK0296jtA==",
            timeout=60000,
        )
        await self._load_rec()
        seclo_db_ok = True
        await self.page.wait_for_load_state()
        total_items = (
            await self.page.locator("#ctl00_Center_lstTrabajadores")
            .locator("li")
            .count()
        )
        total_items += (
            await self.page.locator("#ctl00_Center_lstEmpleadores")
            .locator("li")
            .count()
        )
        total_items += (
            await self.page.locator("#ctl00_Center_lstReprentantes")
            .locator("li")
            .count()
        )
        total_items += (
            await self.page.locator("#ctl00_Center_lstDerechohabientes")
            .locator("li")
            .count()
        )
        self.progress.set_steps(2 + total_items)

        # CLAIM
        await self.progress.increase_progress("Getting claim data...")
        claim_data = SECLOClaimData(
            recid=self.recid or 0,
            legal_stuff=await self.page.locator(
                "#ctl00_Center_ucReclamo_txtComentario"
            ).input_value(),
            init_by_worker=await self.page.locator(
                "#ctl00_Center_ucReclamo_optReclamante_0"
            ).is_checked(),
        )
        for row in (
            await self.page.locator("#ctl00_Center_ucReclamo_chkObjetoReclamo")
            .locator("td")
            .all()
        ):
            if await row.locator("input").is_checked():
                claim_data.add_claim_object(
                    ClaimType.string_to_enum(await row.locator("label").inner_text())
                )
        # EMPLOYEES
        people_list = self.page.locator("#ctl00_Center_lstTrabajadores").locator("li")
        for i in range(await people_list.count()):
            await people_list.nth(i).locator("a").click()
            await self.page.wait_for_load_state()
            employee, seclo_db_ok = await self.__get_employee_data(seclo_db_ok)
            await self.progress.increase_progress(
                f"Employee {employee.name} ({i+1} of {await people_list.count()})"
            )
            claim_data.add_employee(employee)
            if seclo_db_ok:
                await self.page.locator("#ctl00_Center_ctl00_btnAgregar").click()

        # EMPLOYERS
        await self.page.wait_for_load_state()
        people_list = self.page.locator("#ctl00_Center_lstEmpleadores").locator("li")
        for i in range(await people_list.count()):
            await people_list.nth(i).locator("a").click()
            await self.page.wait_for_load_state()
            employer, seclo_db_ok = await self.__get_employer_data(seclo_db_ok)
            await self.progress.increase_progress(
                f"Employer {employer.name} ({i+1} of {await people_list.count()})..."
            )
            claim_data.add_employer(employer)
            if seclo_db_ok:
                await self.page.locator("#ctl00_Center_ctl01_btnAgregar").click()

        # LAWYERS
        await self.page.wait_for_load_state()
        people_list = self.page.locator("#ctl00_Center_lstReprentantes").locator("li")
        for i in range(await people_list.count()):
            await people_list.nth(i).locator("a").click()
            await self.page.wait_for_load_state()
            lawyer = await self.__get_lawyer_data(seclo_db_ok)
            await self.progress.increase_progress(
                f"Lawyer {lawyer.name} ({i+1} of {await people_list.count()})..."
            )
            claim_data.add_lawyer(lawyer)

        # OTHERS
        await self.page.wait_for_load_state()
        people_list = self.page.locator("#ctl00_Center_lstDerechohabientes").locator(
            "li"
        )
        for i in range(await people_list.count()):
            await people_list.nth(i).locator("a").click()
            await self.page.wait_for_load_state()
            other = await self.__get_other_data()
            await self.progress.increase_progress(
                f"Other {other.name} ({i+1} of {await people_list.count()})..."
            )
            claim_data.add_other(other)

        # END
        await self.progress.set_completion("Done getting data.")
        if seclo_db_ok and not DEBUGMODE:
            await self.__save_claim_data()
        return claim_data

    @retry
    async def get_conciliador_data(self: Self) -> str:
        """
        Returns the assigned conciliator for current case.
        """
        await self.page.goto(f"Conciliador_Reclamo.aspx?RecId={self.recid}")

        try:
            return await self.page.locator("#rcConciliador").inner_text(timeout=10000)
        except PlaywrightTimeoutError:
            return "UNKNOWN"

    async def __complete_address_field(self: Self, field: Locator, text: str) -> None:
        if not field.get_attribute("readOnly"):
            await field.fill("")
            await field.fill(text)
            await self.page.locator(".ui-widget-content").is_visible()
            await field.press("Enter")
            await field.press("Tab")
            error_loc = self.page.locator(".divMensajeWarning")
            if await error_loc.is_visible(timeout=1000):
                raise InvalidCaseStateException(
                    f"Address error: {await error_loc.inner_text()}"
                )

    @retry
    async def add_employer(self: Self, employer: SECLOEmployerData) -> Self:
        """
        Attempts to expand a claim with the given employer.
        This can fail in many many ways, but we can try at least.
        Parameters:
            employer (SECLOEmployerData): The employer to be added.
        """
        self.progress.set_steps(1)
        await self.progress.set_progress(0, "Loading claim data form...")
        if not employer.address:
            raise InvalidParameterException("Employer must have address")

        for _ in range(0, 5):
            # Trying to get this bitch enabled. idk why this works but it does.
            await self.page.goto(
                "ingresoreclamos.aspx?paramEnc=AB3u3y2175MqNXK0296jtA==",
                timeout=60000,
            )
            await self._load_rec()
            await self.page.locator("#ctl00_Center_lnkEmpleadores").click()
            cuit_box = self.page.locator("#ctl00_Center_ctl01_cuit_txtC")
            if await cuit_box.is_enabled():
                break
            await self.__save_claim_data()
        else:
            raise InvalidCaseStateException(
                "Couldn't open employer edit menu, you might need to edit this manually"
            )

        await self.page.locator(
            "#ctl00_Center_ctl01_cmbTipoSociedad_cmb"
        ).select_option(
            value=str(
                employer.person_type.value[0]
                if employer.person_type is not None
                else PersonType.PERSON.value[0]
            )
        )

        await self.page.locator("#ctl00_Center_ctl01_cuit_txtC").fill(
            str(employer.cuil)
        )
        await self.page.locator("#ctl00_Center_ctl01_cuit_txtC").press("Tab")
        await self.page.locator("#ctl00_Center_ctl01_cmbActividad_cmb").select_option(
            value="22"
        )
        await self.page.locator("#ctl00_Center_ctl01_txtActividad_txt").fill(
            "alguna actividad misteriosa de la cual desconocemos"
        )
        await self.page.locator("#ctl00_Center_ctl01_txtActividad_txt").press("Tab")

        await self.__complete_address_field(
            self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtProvincia"),
            employer.address.province,
        )
        await self.__complete_address_field(
            self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtPartido"),
            employer.address.district,
        )
        await self.__complete_address_field(
            self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtLocalidad"),
            employer.address.county,
        )
        await self.__complete_address_field(
            self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtCalle"),
            employer.address.street,
        )
        await self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtNumero").fill(
            employer.address.number or ""
        )
        await self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtNumero").press(
            "Tab"
        )
        await self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtPiso").fill(
            employer.address.floor or ""
        )
        await self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtDepart").fill(
            employer.address.apt or ""
        )
        await expect(
            self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtCPA")
        ).to_have_value(re.compile(".+", re.IGNORECASE), timeout=30000)
        cpa = self.page.locator("#ctl00_Center_ctl01_Domicilio_direc_txtCPA")
        if not await cpa.input_value():
            await cpa.fill(employer.address.cpa or "")
        await self.page.locator(
            "#ctl00_Center_ctl01_Domicilio_direc_txtAdicional"
        ).fill(employer.address.bonus_data or "")

        await self.page.locator("#ctl00_Center_ctl01_txtEmail_txt").fill(
            employer.mail or ""
        )
        await self.page.locator("#ctl00_Center_ctl01_txtTelefono_txt").fill(
            str(employer.phone or "")
        )

        if not DEBUGMODE:
            await self.page.locator("#ctl00_Center_ctl01_btnAgregar").click()
            await self.page.wait_for_event("load")
            error_text = (
                await self.page.locator(
                    "#ctl00_Center_ctl01_ValidationSummary1"
                ).inner_text()
            ).strip()
            if error_text:
                raise InvalidCaseStateException(error_text)
        return self


class SECLOInvoiceParser(SECLOAccessor):
    """
    A class for accessing invoices.
    Basically for nonagreements.
    """

    @retry
    async def list_invoices(self: Self) -> List[Dict[str, Any]]:
        """
        Fetches available list of invoices to be selected
        Returns:
            invoices: {'id': int, 'date': datetime}
        """
        await self.page.goto("/FF_ConsultaLiquidaciones.aspx", timeout=60000)
        invoices: List[Dict[str, Any]] = []
        options = self.page.locator("#ctl00_Center_cmbLiquidaciones").locator("option")
        for option in await options.all():
            invoices.append(
                {
                    "id": int(await option.get_attribute("value") or 0),
                    "date": datetime.strptime(
                        (await option.inner_text()).split()[0], "%d/%m/%Y"
                    ),
                }
            )
        return invoices

    @retry
    async def get_invoice_details(self: Self, invoice: int) -> Dict:
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
        await self.page.goto("/FF_ConsultaLiquidaciones.aspx")
        await self.page.locator("#ctl00_Center_cmbLiquidaciones").select_option(
            value=str(invoice)
        )
        await self.page.locator("#ctl00_Center_btnBuscar").click()

        result = []
        table = self.page.locator("#ctl00_Center_grdMovimientos")
        for row in await table.locator(".grdRowStyle").all():
            result.append(
                {
                    "gdeID": await row.locator("td").nth(2).inner_text(),
                    "description": await row.locator("td").nth(3).inner_text(),
                    "amount": Decimal(
                        (await row.locator("td").nth(4).inner_text())[
                            2:-1
                        ]  # Remove pesos sign and space
                        .replace(".", "")
                        .replace(",", ".")
                    ),
                    "date": datetime.strptime(
                        await row.locator("td").nth(5).inner_text(), "%d/%m/%Y"
                    ),
                }
            )
        return {
            "total": Decimal(
                (await self.page.locator("#ctl00_Center_lblTotal").inner_text())
                .split()[1]
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

    def __init__(
        self: Self,
        session: SECLOSession,
        weeks_before: int,
        weeks_after: int,
        progress: ProgressReport | None = None,
    ):
        super().__init__(session, None, progress)
        self.weeks_before = weeks_before
        self.weeks_after = weeks_after
        self.current = 0
        self.first_stage = ProgressReport()
        self.second_stage = ProgressReport()
        self.id_task: asyncio.Task
        self.citation_tasks = []

    async def __aenter__(self: Self) -> Self:
        await super().__aenter__()
        await self.first_stage.set_steps(
            1 + (self.weeks_before + self.weeks_after)
        ).set_message("Loading calendar")
        await self.first_stage.set_progress(0, "Loading calendar")
        self.second_stage.set_steps(1)
        await self.second_stage.set_progress(0, "Loading citation data")
        await self.progress.compose(self.first_stage, "Parsing weeks")
        await self.progress.compose(self.second_stage, "Parsing citations")
        await self.__load_calendar()
        self.id_task: asyncio.Task = asyncio.get_event_loop().create_task(
            self.__populate_calendar_ids()
        )
        return self

    async def __aexit__(self: Self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)

    @retry
    async def __load_calendar(self: Self) -> datetime:
        await self.page.goto("/InicioConciliador.aspx")
        await self.page.locator("#ctl00_Center_chkSusp").click()
        await self.page.locator("#ctl00_Center_chkReal").click()
        await self.page.wait_for_event("load")
        return datetime.strptime(
            await self.page.locator("#ctl00_Center_txtFecha_txt").input_value(),
            "%d/%m/%Y",
        )

    async def __iterate_calendar_week(self: Self) -> List[int]:
        table = self.page.locator("#ctl00_Center_DayPilotCalendar1").locator("tr")
        ids: List[int] = []
        # loop through days
        for day in (
            await table.locator("table").nth(1).locator("tr").first.locator("td").all()
        ):
            # loop through cases in day
            for case in await day.locator("div").locator("div").all():
                aud_id = str(await case.get_attribute("onclick"))
                if aud_id:
                    aud_id = re.search(r"PK:\d+", aud_id)
                    if aud_id:
                        ids.append(int(aud_id.group(0)[3:]))
        return ids

    async def __advance_calendar(self: Self, date: datetime):
        date_textbox = self.page.locator("#ctl00_Center_txtFecha_txt")
        if datetime.strptime(await date_textbox.input_value(), "%d/%m/%Y") is not date:
            await date_textbox.fill("")
            await date_textbox.fill(date.strftime("%d/%m/%Y"))
            await self.page.locator("#ctl00_Center_btnConsultar").click()
            await self.page.wait_for_event("load")
        return datetime.strptime(await date_textbox.input_value(), "%d/%m/%Y")

    async def __iterate_calendar_range(self: Self) -> tuple[bool, list[int]]:
        if self.current <= self.weeks_after and self.weeks_after >= 0:
            await self.__advance_calendar(
                datetime.now() + timedelta(weeks=self.current)
            )
            self.current += 1
            citation_ids = await self.__iterate_calendar_week()
            await self.first_stage.increase_progress(
                f"{self.current} of {self.weeks_before + self.weeks_after}",
            )
            if self.current >= self.weeks_after:
                self.weeks_after = -1
                self.current = 0
            return True, citation_ids
        if self.current < self.weeks_before and self.weeks_before > 0:
            self.current += 1
            await self.__advance_calendar(
                datetime.now() + timedelta(weeks=-self.current)
            )
            citation_ids = await self.__iterate_calendar_week()
            await self.first_stage.increase_progress(
                f"{self.current + self.weeks_after} of {self.weeks_before + self.weeks_after}",
            )
            if self.current >= self.weeks_before:
                self.weeks_before = -1
                self.current = 0
            return True, citation_ids
        await self.first_stage.set_completion("Done")
        return False, []

    @retry
    async def __populate_calendar_ids(self: Self):
        result = True
        while result:
            result, citation_ids = await self.__iterate_calendar_range()
            self.citation_tasks.extend(
                [
                    asyncio.get_event_loop().create_task(self.__get_citation_info(id))
                    for id in citation_ids
                ]
            )
            self.second_stage.set_steps(
                self.second_stage.total_steps + len(citation_ids)
            )

    def __aiter__(self: Self):
        return self

    async def __anext__(self: Self) -> SECLOCitation:
        while len(self.citation_tasks) == 0 and not self.id_task.done():
            await asyncio.sleep(0.01)

        if len(self.citation_tasks) == 0 and self.id_task.done():
            await self.second_stage.set_completion("Done")
            raise StopAsyncIteration

        async for task in asyncio.as_completed(self.citation_tasks):
            self.citation_tasks.remove(task)
            await self.second_stage.increase_progress()
            return task.result()
        else:
            raise StopAsyncIteration  # Not really possible but complains otherwise

    @retry
    async def __get_citation_info(self: Self, citation_id: int) -> SECLOCitation:
        # self.second_stage.increase_progress(f"{index + 1} of {len(ids)}")
        async with SECLOAccessor(self.session) as session:
            await session.page.goto(
                f"Conciliador_Audiencia.aspx?AudId={citation_id}&esPortal=1", 
                timeout=60000
            )
            gde_id_text = await session.page.locator("#rcNroExpediente").inner_text()
            init_datetime_text = await session.page.locator("#rcFecha").inner_text()
            init_datetime_text = (
                init_datetime_text.split()[0]
                + " "
                + init_datetime_text.split()[1].split(":")[0]
                + ":"
                + init_datetime_text.split()[1].split(":")[1]
            )
            citation_date = await session.page.locator("#rcFechaA").inner_text()
            citation_date = citation_date.split("a")[0]
            return SECLOCitation(
                gdeID=gde_id_text,
                citationDate=datetime.strptime(citation_date, r"%d/%m/%Y - %H:%M "),
                initDate=datetime.strptime(init_datetime_text, r"%d/%m/%Y %H:%M"),
                citationID=citation_id,
                citationType=await session.page.locator("#auTipoYEstado").inner_text(),
                pdfString=base64.b64encode(await session.page.pdf()).decode("ascii"),
            )

    @retry
    async def get_calendar(self: Self, date: datetime) -> List[SECLOCitation]:
        """
        Fetches the current calendar assignments from SECLO.
        Ideal entry point for claim registration and validating cases.
        Parameters:
            date (datetime): Override to load a specific week in absolute time.
        """
        await self.__advance_calendar(date)
        ids = await self.__iterate_calendar_week()
        return [await self.__get_citation_info(citation_id) for citation_id in ids]

    @retry
    async def get_workable_days(
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
        await self.progress.set_message("Loading calendar info...")

        await self.page.goto("/pa_Abogados_Audiencias.aspx")
        await self.page.locator("#ctl00_Principal_CmbFormato").select_option(
            value="1"
        )  # per-day
        for day in range(1, weeks_ahead * 7):
            cal = (
                self.page.locator("#ctl00_Principal_DayPilotCalendar1")
                .locator("tr")
                .locator("table")
                .nth(1)
            )
            date = datetime.strptime(
                await self.page.locator(
                    "#ctl00_Principal_txtFecha_txtFecha"
                ).input_value(),
                "%d/%m/%Y",
            )
            day = cal.locator("tr").nth(2).locator("td")
            day_title = await cal.locator("tr").nth(1).locator("td").inner_text()

            if "Feriado" in (await day.get_attribute("title") or ""):
                work_days.append(
                    (
                        date,
                        False,
                        " ".join((await day.get_attribute("title") or "").split()[1:]),
                    )
                )
            elif "dom" in day_title or "sáb" in day_title:
                work_days.append((date, False, day_title))
            else:
                work_days.append((date, True, ""))
            await self.progress.increase_progress(
                f"Obtained info for {date.strftime('%d/%m/%Y')}"
            )
            await self.page.locator("#ctl00_Principal_lnkDer").click()
            await self.page.wait_for_event("load")
        await self.progress.set_completion("Done getting cal info")
        return work_days


class SECLOClaimValidationData(SECLOAccessor):
    """
    Utility class for validating some data throuth a
    very rudimentary api provided by this website.

    Stuff like cuit, dni and addresses
    """

    async def __create_request(self: Self, url: str, data: str) -> str:
        cookies = {}
        cookie_list = await self.session.context.cookies(urls="conciliadores.trabajo.gob.ar")
        for cookie in cookie_list:
            cookies[cookie["name"]] = cookie["value"] # type: ignore
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "es-419,es-US;q=0.9,es;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json; charset=UTF-8",
            "Dnt": "1",
            "Host": "conciliadores.trabajo.gob.ar",
            "Origin": "https://conciliadores.trabajo.gob.ar",
            "Refererer": "https://conciliadores.trabajo.gob.ar/ingresoreclamos.aspx",
            "sec-ch-ua-platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
        }

        ans = await self.session.context.request.post(url, headers=headers, data=data)
        return await ans.json()

    def validate_cuit(self: Self, cuit: str):
        """
        Tries to validate the given CUIT.
        """
        return self.__create_request(
            "/ServicioCuit.aspx/GetDatosCOmpletosxCuit",
            "{'dato': '" + cuit + "'}",
        )

    def validate_dni(self: Self, dni: str):
        """
        Tries to validate the given dni.
        """
        return self.__create_request(
            "/ServicioDocumento.aspx/getDatosxDenominacion",
            "{'dato': '" + dni + "', 'tipo': 'E'}",
        )

    def validate_district(self: Self, province: str, district: str):
        """
        Tries to validate the given district (for given province).
        """
        return self.__create_request(
            "/ServicioCPA.aspx/GetPartidos",
            "{'dato': '" + district + "', 'prov': '" + province + "'}",
        )

    def validate_county(self: Self, province: str, district: str, county: str):
        """
        Tries to validate the given county (for given province and district).
        """
        return self.__create_request(
            "/ServicioCPA.aspx/GetLocalidades",
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
            "/ServicioCPA.aspx/GetCalles",
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
            "/ServicioCPA.aspx/getCPA",
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
            "/ServicioCPA.aspx/GetCallesHelper",
            "{"
            + f'\'prov\': \'{province}\', \'part\': \'{(district or "")}\', '
            + f'\'localidad\': \'{(county or "")}\', \'calle\': \'{street}\''
            + "}",
        )


if __name__ == "__main__":
    raise RuntimeError("This script cannot be run on its own")
