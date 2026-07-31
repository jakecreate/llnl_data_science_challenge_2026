from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ---------------------------------------------------------
# 1. Lit -> TDS Hand-off
# ---------------------------------------------------------
class AnalysisMethod(BaseModel):
    name: str = Field(..., description="Name of the analysis method")
    description: str = Field(..., description="Detailed explanation of the method")

class LitOutputPayload(BaseModel):
    lattice_type: str
    specific_type: str
    data_file_path: str
    selected_methods: List[AnalysisMethod] = Field(..., min_items=2, max_items=3)

# ---------------------------------------------------------
# 2. TDS -> Human Checkpoint (2.5) Hand-off
# ---------------------------------------------------------
class TDSPlanPayload(BaseModel):
    status: Literal["requires_human_approval"] = "requires_human_approval"
    data_file_path: str
    is_valid_3d_tif: bool = Field(..., description="Result of the early metadata check")
    required_packages: List[str] = Field(..., description="Python/System packages to install")
    implementation_steps: List[str] = Field(..., description="Ordered steps for CodA")

# ---------------------------------------------------------
# 3. Human Checkpoint -> CodA Hand-off
# ---------------------------------------------------------
class HumanApprovalPayload(BaseModel):
    approved: bool
    feedback: Optional[str] = Field(None, description="Revision notes if not approved")
    approved_packages: List[str] = Field(default_factory=list)
    approved_steps: List[str] = Field(default_factory=list)

# ---------------------------------------------------------
# 4. CodA -> Eval Hand-off
# ---------------------------------------------------------
class CodAArtifactsPayload(BaseModel):
    status: Literal["success", "error"]
    ipynb_path: Optional[str] = Field(None, description="Path to raw Jupyter notebook")
    pdf_path: Optional[str] = Field(None, description="Path to rendered PDF report")
    execution_logs: str = Field(..., description="Standard output/error from the sandbox")

# ---------------------------------------------------------
# 5. Eval -> Routing (CodA or TDS or Final) Hand-off
# ---------------------------------------------------------
class EvalFeedbackPayload(BaseModel):
    passed: bool
    error_type: Optional[Literal["A", "B"]] = Field(
        None, 
        description="Type A goes to CodA. Type B goes to TDS. None if passed."
    )
    step_completeness_check: bool
    visual_inspection_check: bool
    proofreading_check: bool
    data_integrity_check: bool
    feedback_instructions: str = Field(..., description="Specific fix instructions")
    unresolved_flag: bool = Field(False, description="True if max iterations exceeded")