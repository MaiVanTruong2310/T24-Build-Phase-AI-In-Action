with open('src/api/endpoints/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace limit default and max
old_limit = 'limit: int = Query(default=50, ge=1, le=100),'
new_limit = 'limit: int = Query(default=100, ge=1, le=250),'

content = content.replace(old_limit, new_limit, 1)

# Add categories endpoint before get_public_service
categories_endpoint = '''@router.get("/services/categories", response_model=ApiResponse[list[str]])
async def list_service_categories(
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[str]]:
    """List distinct categories of active medical services and health packages."""
    from sqlalchemy import select, distinct
    from src.models.catalog import Service
    async with service.session as s:
        stmt = select(distinct(Service.category)).where(Service.status == "active", Service.category.is_not(None)).order_by(distinct(Service.category))
        res = await s.execute(stmt)
        categories = [c for c in res.scalars().all() if c and c != "Khám Chuyên Khoa"]
    return success_response(categories, "Categories retrieved")


'''

target = '@router.get("/services/{service_id}", response_model=ApiResponse[ServiceResponse])'
if target in content and categories_endpoint not in content:
    content = content.replace(target, categories_endpoint + target, 1)

with open('src/api/endpoints/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated src/api/endpoints/service.py successfully")
