import re
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RelativeInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    gender: Literal['male', 'female', 'other', 'prefer_not_to_say']
    relationship: Literal['parent', 'child', 'spouse', 'sibling', 'grandparent', 'other']
    contact_phone: str = Field(max_length=20)
    citizen_id: str | None = Field(default=None, pattern=r'^\d{12}$')
    health_insurance_code: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    consent_to_manage: bool

    @field_validator('contact_phone')
    @classmethod
    def phone(cls, value):
        value = re.sub(r'[\s.()-]', '', value)
        if not re.fullmatch(r'^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$', value):
            raise ValueError('Số điện thoại liên hệ không hợp lệ.')
        return value

    @model_validator(mode='after')
    def validate_profile(self):
        today = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
        if self.date_of_birth > today:
            raise ValueError('Ngày sinh không được ở tương lai.')
        min_year = today.year - 150
        try:
            min_dob = today.replace(year=min_year)
        except ValueError:
            min_dob = date(min_year, 2, 28)
        if self.date_of_birth < min_dob:
            raise ValueError('Ngày sinh không hợp lệ: tuổi không được vượt quá 150 tuổi.')
        if not self.consent_to_manage:
            raise ValueError('Cần xác nhận được người khám hoặc người giám hộ đồng ý quản lý hồ sơ đặt lịch.')
        return self
