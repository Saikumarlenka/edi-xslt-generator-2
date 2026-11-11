from typing import Any, Optional
from pydantic import BaseModel, Field

class ReviewPoint(BaseModel):
    mapping_id: str
    destination_element: str
    destination_segment: str = ""
    source_document_reference: str = ""
    source_canonical_path: str = ""
    suggested_canonical_path: str = ""
    loop_context: str = ""
    loop_relative_path: str = ""
    suggested_loop_path: str = ""
    issue_type: str = "spelling"  # "spelling" | "container_structure" | "path_completion" | "unresolved"
    message: str = ""
    confidence: float = 1.0
    status: str = "applied"  # "applied" | "suggested" | "reverted"

class MappingRecord(BaseModel):
    mapping_id: str = "unknown"
    source_document_reference: str = "unknown"
    source_description: str = "not_specified"
    source_canonical_path: str = "unknown"
    destination_segment: str = "unknown"
    destination_element: str = "unknown"
    mapping_rule: str = "not_specified"
    conditions: list[str] = Field(default_factory=list)
    constants: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)
    default_behavior: str = "not_specified"
    related_notes: list[str] = Field(default_factory=list)
    source_path_resolution_status: str = "unresolved"
    destination_schema_status: str = "unresolved"
    ambiguities: list[str] = Field(default_factory=list)
    implementation_status: str = "unresolved"
    proposed_xpath: str | None = None
    patch_id: str | None = None
    is_crossed: bool = False
    is_constant: bool = False
    is_not_in_schema: bool = False
    user_confirmation: str | None = None  # "ignore" | "keep" | None
    parent_segment: str = ""
    parent_path: str = ""
    parent_condition: str = ""
    loop_context: str = ""
    loop_relative_path: str = ""
    extraction_method: str = "python"
    suggested_canonical_path: str | None = None
    path_correction_reason: str | None = None
    schema_validation_status: str = "valid"  # "valid" | "corrected" | "not_in_schema" | "constant"

class MappingSpecification(BaseModel):
    transaction: str
    document_summary: str = ""
    mappings: list[MappingRecord]
    document_warnings: list[str] = Field(default_factory=list)
    extraction_method: str = "python"
    review_points: list[ReviewPoint] = Field(default_factory=list)

class GenerationRequest(BaseModel):
    transaction: str

class ClarificationRequest(BaseModel):
    clarifications: dict[str, str]

class PatchProposal(BaseModel):
    mapping_id: str
    action: str = "unresolved"
    target_xpath: str | None = None
    expression: str | None = None
    explanation: str = ""
    confidence: str = "low"

class ValidationItem(BaseModel):
    name: str
    status: str
    details: str = ""

class JobState(BaseModel):
    job_id: str
    transaction: str
    status: str
    stage: str
    message: str = ""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mapping_count: int = 0
    created_at: str
