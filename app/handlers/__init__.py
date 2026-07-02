from aiogram import Router

from . import menu, upload, payments as payments_handlers, admin


def get_router() -> Router:
    root = Router()
    root.include_router(menu.router)
    root.include_router(upload.router)
    root.include_router(payments_handlers.router)
    root.include_router(admin.router)
    return root
