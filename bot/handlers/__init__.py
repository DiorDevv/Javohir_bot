"""Routerlar tartibi muhim: /start birinchi, admin buyruqlari so'rovnoma fallback'laridan oldin."""
from __future__ import annotations

from aiogram import Router

from bot.handlers import admin, start, survey


def get_routers() -> list[Router]:
    return [start.router, admin.router, survey.router]


__all__ = ["get_routers"]
