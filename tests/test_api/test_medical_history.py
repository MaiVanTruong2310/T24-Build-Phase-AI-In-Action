from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from pydantic import ValidationError
from src.models.user import User
from src.schemas.auth import UpdateProfileRequest
from src.services.auth import AuthService

@pytest.mark.asyncio
async def test_medical_history_can_change_status_without_changing_other_details():
    session=AsyncMock(); session.begin=MagicMock(return_value=AsyncMock())
    condition={'id':str(uuid4()),'name':'Profile test condition','status':'in_treatment'}
    user=User(id=uuid4(),patient_details={'blood_type':'O+','medical_history':[condition]})
    await AuthService(session).update_profile(user,UpdateProfileRequest(patient_details={'medical_history':[{**condition,'status':'recovered'}]}))
    assert user.patient_details['medical_history'][0]['status']=='recovered'
    assert user.patient_details['blood_type']=='O+'

@pytest.mark.parametrize('name,status',[('   ','in_treatment'),('Test','normal'),('Test','')])
def test_medical_history_rejects_empty_names_and_unknown_status(name,status):
    with pytest.raises(ValidationError): UpdateProfileRequest(patient_details={'medical_history':[{'id':str(uuid4()),'name':name,'status':status}]})
