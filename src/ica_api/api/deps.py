"""Dependencias compartidas por las rutas HTTP."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from ica_api.core.config import Settings, get_settings
from ica_api.infra.db.session import get_session

DBSession = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
