with open('src/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_target = 'from src.api.endpoints.notification import router as notification_router'
import_repl = 'from src.api.endpoints.package import router as package_router, staff_router as staff_package_router\nfrom src.api.endpoints.notification import router as notification_router'

route_target = 'app.include_router(notification_router, prefix="/api/v1")'
route_repl = 'app.include_router(notification_router, prefix="/api/v1")\napp.include_router(package_router, prefix="/api/v1")\napp.include_router(staff_package_router, prefix="/api/v1")'

if import_target in content and route_target in content:
    content = content.replace(import_target, import_repl, 1).replace(route_target, route_repl, 1)
    with open('src/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated src/main.py successfully")
else:
    print("Targets not found")
