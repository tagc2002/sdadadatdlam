"""Module for managing agreements."""
import logging

from fastapi import APIRouter
from api.dtos.DTOs import AgreementDTO

logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/claim/{recID}/agreement')

@router.post('')
def create_agreement(rec_id: int, agreement_data: AgreementDTO):
    #agreementManager.createAgreement(recID, agreementData.toSQL())
    return 