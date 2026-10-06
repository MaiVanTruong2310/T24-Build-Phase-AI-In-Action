import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import select, update
from src.db.session import get_session_factory
from src.models.service import Service

def categorize(name: str) -> str:
    n = name.lower()
    if 'thẻ vinmec' in n or 'thẻ' in n:
        return 'Thẻ đặc quyền y tế'
    if 'tổng quát' in n:
        return 'Khám sức khỏe tổng quát'
    if 'tầm soát' in n or 'ung thư' in n or 'đột quỵ' in n:
        return 'Tầm soát chuyên sâu'
    if 'phục hồi' in n or 'trị liệu' in n or 'nắn chỉnh' in n or 'vận động' in n:
        return 'Phục hồi chức năng'
    if 'trẻ' in n or 'kid' in n or 'long đờm' in n:
        return 'Nhi khoa & Chăm sóc trẻ'
    if 'thai' in n or 'ở cữ' in n or 'her' in n or 'sản' in n:
        return 'Sản phụ khoa & Mẹ và Bé'
    if 'hội thảo' in n:
        return 'Sự kiện y khoa'
    return 'Lộ trình chăm sóc đặc biệt'

async def run():
    factory = get_session_factory()
    async with factory() as session:
        # 1. Update DV-KHAN-CHUYEN-KHOA
        await session.execute(
            update(Service)
            .where(Service.code == 'DV-KHAN-CHUYEN-KHOA')
            .values(category='Khám Chuyên Khoa', status='active')
        )
        
        # 2. Get all other services
        stmt = select(Service).where(Service.code != 'DV-KHAN-CHUYEN-KHOA')
        services = (await session.execute(stmt)).scalars().all()
        print(f"Updating {len(services)} package services...")
        
        updated_count = 0
        for s in services:
            cat = categorize(s.name)
            # Active all packages except free workshops if needed, or active all
            new_status = 'active'
            s.category = cat
            s.status = new_status
            updated_count += 1
            
        await session.commit()
        print(f"Successfully updated and activated {updated_count} package services!")

if __name__ == '__main__':
    asyncio.run(run())
