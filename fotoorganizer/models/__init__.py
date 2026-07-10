"""Modelos ORM do catálogo. Importar tudo aqui garante que Base.metadata
enxerga todas as tabelas (necessário para o Alembic)."""

from fotoorganizer.models.base import Base
from fotoorganizer.models.catalog import (
    MediaFile,
    MetadataEntry,
    ScanSession,
    ScanStatus,
    Source,
)
from fotoorganizer.models.duplicates import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
)
from fotoorganizer.models.geo import Event, Location, Trip
from fotoorganizer.models.inference import (
    ConfidenceLevel,
    Evidence,
    Suggestion,
    SuggestionStatus,
    suggestion_evidence,
)
from fotoorganizer.models.operations import (
    AuditLog,
    OperationItem,
    OperationPlan,
    OperationStatus,
)
from fotoorganizer.models.people import (
    FaceEmbedding,
    FaceOccurrence,
    FaceState,
    Person,
)
from fotoorganizer.models.settings import ApplicationSetting
from fotoorganizer.models.tagging import MediaTag, Tag

__all__ = [
    "Base",
    "Source", "ScanSession", "ScanStatus", "MediaFile", "MetadataEntry",
    "Location", "Trip", "Event",
    "Person", "FaceEmbedding", "FaceOccurrence", "FaceState",
    "Tag", "MediaTag",
    "Evidence", "Suggestion", "SuggestionStatus", "ConfidenceLevel",
    "suggestion_evidence",
    "DuplicateGroup", "DuplicateMember", "DuplicateLevel", "DuplicateRole",
    "OperationPlan", "OperationItem", "OperationStatus", "AuditLog",
    "ApplicationSetting",
]
