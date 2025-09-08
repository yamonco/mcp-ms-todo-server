from __future__ import annotations
from fastapi import APIRouter

from . import api_keys as api_keys_mod
from . import tokens as tokens_mod
from . import apps as apps_mod
from . import groups as groups_mod
from . import policy as policy_mod


router = APIRouter()

router.include_router(api_keys_mod.router)
router.include_router(tokens_mod.router)
router.include_router(apps_mod.router)
router.include_router(groups_mod.router)
router.include_router(policy_mod.router)

