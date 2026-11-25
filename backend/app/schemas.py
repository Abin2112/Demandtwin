from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Segment = Literal["value", "balanced", "premium"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Credentials(Input):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]
    password: Annotated[str, StringConstraints(min_length=10, max_length=128)]


class Registration(Credentials):
    research_code: str | None = Field(default=None, max_length=200)


class ProjectInput(Input):
    name: Name
    description: Text = ""


class MemberInput(Input):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]


class Alternative(Input):
    name: Name
    price: float = Field(gt=0, le=100000)
    grams: float = Field(gt=0, le=5000)
    flavour: Literal["classic", "spicy"] = "classic"
    packaging: Literal["standard", "resealable"] = "standard"
    positioning: Literal["standard", "premium"] = "standard"


class ProductDetails(Alternative):
    category: Name = "Packaged snacks"
    location: Name = "Mumbai"
    segment: Segment = "balanced"
    description: Text = ""
    ingredients: Text = ""
    features: Text = ""
    packaging_image: Annotated[str, StringConstraints(max_length=1500, pattern=r"^(https://[^\s]+|/api/v1/products/[0-9a-f-]{36}/image)$")] | None = None
    cost: float | None = Field(default=None, ge=0, le=100000)
    competitors: list[Alternative] = Field(default_factory=list, max_length=5)


class ProductInput(ProductDetails):
    project_id: UUID


class StudyPolicy(Input):
    strategy: Literal["random", "balanced", "adaptive"] = "random"
    task_limit: int = Field(default=6, ge=1, le=24)
    max_products: int = Field(default=6, ge=2, le=6)
    min_price: float = Field(default=0, ge=0, le=100000)
    max_price: float = Field(default=100000, gt=0, le=100000)
    coverage_penalty: float = Field(default=0.5, ge=0, le=2)
    segment_quotas: dict[Segment, Annotated[int, Field(ge=1, le=100000)]] = Field(default_factory=dict, max_length=3)

    @model_validator(mode="after")
    def price_order(self):
        if self.min_price >= self.max_price:
            raise ValueError("Minimum price must be below maximum price")
        return self


class ExperimentInput(Input):
    project_id: UUID
    name: Name
    synthetic: bool = True
    designs: list[Annotated[list[Alternative], Field(min_length=2, max_length=6)]] = Field(min_length=3, max_length=24)
    policy: StudyPolicy = Field(default_factory=StudyPolicy)


class Consent(Input):
    segment: Segment
    adult: Literal[True]
    consent: Literal[True]
    version: Annotated[str, StringConstraints(pattern=r"^v1(-[0-9a-f]{20})?$")]
    synthetic: bool


class Choice(Input):
    task: int = Field(ge=0, lt=24)
    chosen: int = Field(ge=0, le=6)


class Training(Input):
    experiment_id: UUID
    seed: int = Field(default=42, ge=0, lt=2**32)


class Scenario(Input):
    name: Name
    product: Alternative
    competitors: list[Alternative] = Field(default_factory=list, max_length=5)
    opportunities: int = Field(ge=1, le=100_000_000)
    segment_weights: dict[Segment, Annotated[float, Field(gt=0, le=100)]] = Field(min_length=1, max_length=3)


class SimulationInput(Scenario):
    model_id: UUID


class Comparison(Input):
    model_id: UUID
    scenarios: list[Scenario] = Field(min_length=2, max_length=12)


class DesignInput(Input):
    model_id: UUID | None = None
    segment: Segment = "balanced"
    strategy: Literal["adaptive", "balanced", "random"] = "adaptive"
    seed: int = Field(default=42, ge=0, lt=2**32)


class ReportInput(Input):
    simulation_id: UUID
