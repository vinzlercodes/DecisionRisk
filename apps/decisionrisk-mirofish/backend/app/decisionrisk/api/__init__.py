"""DecisionRisk API routes."""

from flask import Blueprint

decisionrisk_bp = Blueprint("decisionrisk", __name__)

from . import artifacts  # noqa: E402,F401
from . import runtime  # noqa: E402,F401
