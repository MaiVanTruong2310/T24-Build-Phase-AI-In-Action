import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
from src.db.session import get_session_factory

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.package_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES public.users(id) ON DELETE RESTRICT,
    service_id UUID NOT NULL REFERENCES public.services(id) ON DELETE RESTRICT,
    facility_id UUID NOT NULL REFERENCES public.facilities(id) ON DELETE RESTRICT,
    preferred_date DATE NOT NULL,
    preferred_period VARCHAR(12) NOT NULL DEFAULT 'morning',
    patient_name VARCHAR(120),
    patient_phone VARCHAR(20),
    patient_email VARCHAR(320),
    gender VARCHAR(16),
    date_of_birth DATE,
    note TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    staff_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_package_requests_patient_created ON public.package_requests (patient_id, created_at);
CREATE INDEX IF NOT EXISTS ix_package_requests_service ON public.package_requests (service_id);
CREATE INDEX IF NOT EXISTS ix_package_requests_status ON public.package_requests (status);
"""

async def run():
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text(CREATE_TABLE_SQL))
        await session.commit()
        print("Successfully created package_requests table and indexes!")

if __name__ == '__main__':
    asyncio.run(run())
