"""Module for managing agreements."""
import logging

from typing import List
from fastapi import APIRouter
from api.dtos.DTOs import AgreementDTO
from database.dbsessionmanager import DependsDb

logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/agreement')

@router.post('')
def create_agreement(agreement_data: AgreementDTO):
    #agreementManager.createAgreement(recID, agreementData.toSQL())
    return 

@router.get('')
def get_agreements(db: DependsDb) -> List[AgreementDTO]:
    return []