# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

JsonScalar = str | int | float | bool | None


class SignificanceTest(str, Enum):
    T_TEST = "t-test"
    PERMUTATION = "permutation"


class Segmentation(str, Enum):
    WHOLE_SERIES = "whole-series"
    SPLIT_MERGE = "split-merge"


class AnalysisOptionsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    window_len: int = 50
    max_pvalue: float = 0.001
    min_magnitude: float = 0.0
    significance_test: SignificanceTest = SignificanceTest.T_TEST
    segmentation: Segmentation = Field(default=Segmentation.SPLIT_MERGE, validate_default=True)

    @field_validator("significance_test", "segmentation")
    @classmethod
    def validate_supported_pair(cls, value: SignificanceTest | Segmentation, info: ValidationInfo):
        significance_test = value if info.field_name == "significance_test" else info.data.get("significance_test")
        segmentation = value if info.field_name == "segmentation" else info.data.get("segmentation")
        if significance_test == SignificanceTest.PERMUTATION and segmentation == Segmentation.SPLIT_MERGE:
            raise ValueError(
                "Permutation significance with split-merge segmentation is not supported; "
                "use whole-series segmentation"
            )
        return value


class MetricModel(BaseModel):
    direction: Optional[int] = None
    scale: Optional[float] = None
    unit: str = ""


class ChangePointModel(BaseModel):
    metric: Optional[str] = None
    index: int
    qhat: float
    forward_change_percent: float
    magnitude: float
    mean_before: float
    stddev_before: float
    mean_after: float
    stddev_after: float
    pvalue: float


class ChangePointGroupModel(BaseModel):
    time: int | float
    attributes: Dict[str, JsonScalar]
    changes: List[ChangePointModel]


class AnalyzedSeriesModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=False)

    test_name: str
    time: List[int | float]
    change_points_timestamp: datetime
    branch_name: Optional[str] = None
    options: AnalysisOptionsModel
    metrics: Dict[str, MetricModel]
    attributes: Dict[str, List[JsonScalar]]
    data: Dict[str, List[Optional[float]]]
    change_points: Dict[str, List[ChangePointGroupModel]]
    weak_change_points: Dict[str, List[ChangePointGroupModel]]
