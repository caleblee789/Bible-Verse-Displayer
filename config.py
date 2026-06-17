# Copyright (c) ijgnord.

import os
from typing import TypeVar, cast

from aqt import mw

T = TypeVar("T")


def gc(key: str, default: T) -> T:
    conf = mw.addonManager.getConfig(__name__)
    if not conf:
        return default
    return cast(T, conf.get(key, default))

addon_folder_abs_path = os.path.dirname(__file__)
foldername = os.path.basename(addon_folder_abs_path)  # mw.addonManager.addonFromModule(__name__)
addonname = mw.addonManager.addonName(foldername)
