"""Service layer: orchestration over domain models.

Scoring lives here (Phase 5); the AI content service (Phase 6) and the discovery
pipeline join later. Services depend on domain + config, never the reverse.
"""

from __future__ import annotations

from lead_intel.services.lead_scorer import LeadScorer
from lead_intel.services.pipeline import (
    LeadPipeline,
    PipelineConfig,
    PipelineResult,
    ProgressEvent,
    build_pipeline,
)
from lead_intel.services.recommender import PackageRecommender
from lead_intel.services.scoring_service import ScoringResult, ScoringService
from lead_intel.services.website_scorer import WebsiteScorer

__all__ = [
    "LeadScorer",
    "PackageRecommender",
    "ScoringResult",
    "ScoringService",
    "WebsiteScorer",
    "LeadPipeline",
    "PipelineConfig",
    "PipelineResult",
    "ProgressEvent",
    "build_pipeline",
]
