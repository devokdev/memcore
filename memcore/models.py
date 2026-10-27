"""Data models and schemas for MemCore."""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, enum.Enum):
    ARCHITECTURE = "architecture"
    CODE_LOCATION = "code_location"
    API_CONTRACT = "api_contract"
    DB_SCHEMA = "db_schema"
    CONVENTION = "convention"
    BUG_FIX = "bug_fix"
    SECURITY_CONSTRAINT = "security_constraint"
    DECISION = "decision"
    DEPENDENCY = "dependency"
    GENERAL = "general"


class MemoryStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPRESSED = "compressed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    SOFT_DELETED = "soft_deleted"


class RelationshipType(str, enum.Enum):
    RELATED_TO = "RELATED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    CONTRADICTS = "CONTRADICTS"
    DUPLICATES = "DUPLICATES"
    SUPERSEDES = "SUPERSEDES"
    DERIVED_FROM = "DERIVED_FROM"
    USED_BY = "USED_BY"
    SUPPORTED_BY = "SUPPORTED_BY"


class GCAction(str, enum.Enum):
    KEEP = "KEEP"
    UPDATE = "UPDATE"
    COMPRESS = "COMPRESS"
    MERGE = "MERGE"
    ARCHIVE = "ARCHIVE"
    SUPERSEDE = "SUPERSEDE"
    PROTECT = "PROTECT"
    DELETE = "DELETE"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    STALE = "stale"
    CONFLICT = "conflict"


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = "default"
    content: str
    memory_type: MemoryType = MemoryType.GENERAL
    source: str = "agent"  # user, conversation, repo_analysis, tool_result, task
    provenance: Dict[str, Any] = Field(default_factory=dict)  # file, line, commit, session_id
    
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_verified_at: Optional[float] = None
    
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    usage_count: int = 0
    last_accessed_at: Optional[float] = None
    
    token_count: int = 0
    estimated_token: bool = False
    
    associated_files: List[str] = Field(default_factory=list)
    associated_symbols: List[str] = Field(default_factory=list)
    associated_components: List[str] = Field(default_factory=list)
    
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    is_protected: bool = False
    protection_reason: Optional[str] = None
    
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_notes: Optional[str] = None
    
    superseded_by: Optional[str] = None
    parent_memory_ids: List[str] = Field(default_factory=list)  # for compressed/merged


class MemoryRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    rel_type: RelationshipType
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryAuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str
    action: str  # create, update, compress, merge, archive, supersede, delete, restore, protect
    timestamp: float = Field(default_factory=time.time)
    actor: str = "system"
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class VerificationResult(BaseModel):
    memory_id: str
    status: VerificationStatus
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    proposed_resolution: Optional[str] = None
    verified_at: float = Field(default_factory=time.time)


class UtilityScore(BaseModel):
    memory_id: str
    score: float
    relevance: float = 0.0
    recency: float = 0.0
    frequency: float = 0.0
    importance: float = 0.0
    confidence: float = 0.0
    verification_bonus: float = 0.0
    dependency_weight: float = 0.0
    breakdown: Dict[str, float] = Field(default_factory=dict)


class RiskScore(BaseModel):
    memory_id: str
    risk_score: float  # 0.0 (safe to delete) to 1.0 (extremely dangerous)
    security_risk: float = 0.0
    critical_type_risk: float = 0.0
    dependency_risk: float = 0.0
    protected_risk: float = 0.0
    uniqueness_risk: float = 0.0
    factors: List[str] = Field(default_factory=list)


class GCRecommendation(BaseModel):
    memory_id: str
    action: GCAction
    utility: float
    risk: float
    reason: str
    candidate_merge_with: Optional[str] = None
    target_content: Optional[str] = None
    requires_approval: bool = False


class RetrievedMemory(BaseModel):
    memory: MemoryRecord
    relevance_score: float
    retrieval_reasons: List[str] = Field(default_factory=list)
    relationships: List[MemoryRelationship] = Field(default_factory=list)
    risk_level: float = 0.0


class ContextBuildResult(BaseModel):
    project_id: str
    task_query: str
    token_budget: int
    used_tokens: int
    budget_utilization_pct: float
    selected_memories: List[RetrievedMemory]
    excluded_memories: List[Dict[str, Any]]
    preserved_dependencies: List[str]
    conflicts_detected: List[str]
    compression_applied: bool
