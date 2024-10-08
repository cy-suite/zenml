#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the Great Expectations materializers."""

import os
import re
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type, Union, cast
import json

from great_expectations.checkpoint.checkpoint import Checkpoint, CheckpointResult
from great_expectations.core import (  # type: ignore[import-untyped]
    ExpectationSuite,
)
from great_expectations.core.expectation_validation_result import (  # type: ignore[import-untyped]
    ExpectationSuiteValidationResult,
)

from great_expectations.data_context.types.resource_identifiers import (
    ExpectationSuiteIdentifier,
    ValidationResultIdentifier,
)
from great_expectations.types import (  # type: ignore[import-untyped]
    SerializableDictDot,
)

from zenml.enums import ArtifactType, VisualizationType
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import source_utils, yaml_utils
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

ARTIFACT_FILENAME = "artifact.json"


class GreatExpectationsMaterializer(BaseMaterializer):
    """Materializer to read/write Great Expectation objects."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        ExpectationSuite,
        CheckpointResult,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = (
        ArtifactType.DATA_ANALYSIS
    )

    @staticmethod
    def preprocess_checkpoint_result_dict(
        artifact_dict: Dict[str, Any],
    ) -> None:
        """Pre-processes a GE checkpoint dict before it is used to de-serialize a GE CheckpointResult object.

        The GE CheckpointResult object is not fully de-serializable
        due to some missing code in the GE codebase. We need to compensate
        for this by manually converting some of the attributes to
        their correct data types.

        Args:
            artifact_dict: A dict containing the GE checkpoint result.
        """

        def preprocess_run_result(key: str, value: Any) -> Any:
            if key == "validation_result":
                return ExpectationSuiteValidationResult(**value)
            return value

        # artifact_dict["checkpoint_config"] = Checkpoint(
        #     **json.loads(artifact_dict["checkpoint_config"])
        # )
        artifact_dict["checkpoint_config"] = Checkpoint(name="test", validation_definitions=[])
        validation_dict = {}
        for result_ident, results in artifact_dict["run_results"].items():
            after_double_colon = result_ident.split('::', 1)[1]

            # Use a regular expression to extract the JSON part
            json_match = re.search(r'\{.*?\}', after_double_colon, re.DOTALL)
            if json_match:
                run_id_json_str = json_match.group(0)
                # Parse the JSON string to extract run_name and run_time
                run_id_data = json.loads(run_id_json_str)

                # Extract run_name and run_time
                run_name = run_id_data.get("run_name")
                run_time = run_id_data.get("run_time")

            # Now split the remaining part by colons to get the components
            components = after_double_colon.split(':')
            expectation_suite_identifier = components[0]
            batch_identifier = components[-1]
            validation_ident_tuple = (expectation_suite_identifier, run_name, run_time, batch_identifier)
            validation_ident = (
                ValidationResultIdentifier.from_fixed_length_tuple(  # type: ignore[no-untyped-call]
                    validation_ident_tuple
                )
            )
            validation_results = {
                result_name: preprocess_run_result(result_name, result)
                for result_name, result in results.items()
            }
            validation_dict[validation_ident] = validation_results
        artifact_dict["run_results"] = validation_dict

    def load(self, data_type: Type[Any]) -> SerializableDictDot:
        """Reads and returns a Great Expectations object.

        Args:
            data_type: The type of the data to read.

        Returns:
            A loaded Great Expectations object.
        """
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = yaml_utils.read_json(filepath)
        data_type = source_utils.load(artifact_dict.pop("data_type"))
        # load active data context
        _ = GreatExpectationsDataValidator.get_data_context()

        if data_type is CheckpointResult:
            self.preprocess_checkpoint_result_dict(artifact_dict)

        return data_type(**artifact_dict)

    def save(self, obj: SerializableDictDot) -> None:
        """Writes a Great Expectations object.

        Args:
            obj: A Great Expectations object.
        """
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = self.serialize_ge_object(obj)
        artifact_type = type(obj)
        artifact_dict["data_type"] = (
            f"{artifact_type.__module__}.{artifact_type.__name__}"
        )
        yaml_utils.write_json(filepath, artifact_dict)

    def serialize_ge_object(self, obj: Any) -> Any:
        """Serialize a Great Expectations object to a JSON-serializable structure.

        Args:
            obj: A Great Expectations object.

        Returns:
            A JSON-serializable representation of the object.
        """
        if isinstance(obj, CheckpointResult):
            return {
                "name": obj.name,
                "run_id": self.serialize_ge_object(obj.run_id),
                "run_results": self.serialize_ge_object(obj.run_results),
                "checkpoint_config": self.serialize_ge_object(obj.checkpoint_config),
                "success": obj.success,
            }
        elif isinstance(obj, dict):
            return {self.serialize_key(k): self.serialize_ge_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.serialize_ge_object(v) for v in obj]
        elif hasattr(obj, 'to_json_dict'):
            return obj.to_json_dict()   
        elif hasattr(obj, 'to_tuple'):
            return obj.to_tuple()
        elif hasattr(obj, 'json'):
            return obj.json()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return obj

    def serialize_key(self, key: Any) -> str:
        """Serialize a dictionary key to a string.

        Args:
            key: The key to serialize.

        Returns:
            A string representation of the key.
        """
        if isinstance(key, (str, int, float, bool)) or key is None:
            return str(key)
        elif isinstance(key, (ExpectationSuiteIdentifier, ValidationResultIdentifier)):
            return self.serialize_identifier(key)
        else:
            return str(key)

    def serialize_identifier(self, identifier: Union[ExpectationSuiteIdentifier, ValidationResultIdentifier]) -> str:
        """Serialize ExpectationSuiteIdentifier or ValidationResultIdentifier to a string.

        Args:
            identifier: The identifier to serialize.

        Returns:
            A string representation of the identifier.

        Raises:
            ValueError: If the identifier type is not supported.
        """
        if isinstance(identifier, ExpectationSuiteIdentifier):
            return f"ExpectationSuiteIdentifier:{identifier.expectation_suite_name}"
        elif isinstance(identifier, ValidationResultIdentifier):
            return f"ValidationResultIdentifier:{identifier.expectation_suite_identifier}:{identifier.run_id}:{identifier.batch_identifier}"

    def save_visualizations(
        self, data: Union[ExpectationSuite, CheckpointResult]
    ) -> Dict[str, VisualizationType]:
        """Saves visualizations for the given Great Expectations object.

        Args:
            data: The Great Expectations object to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        visualizations = {}

        if isinstance(data, CheckpointResult):
            result = cast(CheckpointResult, data)
            identifier = next(iter(result.run_results.keys()))
        else:
            suite = cast(ExpectationSuite, data)
            identifier = ExpectationSuiteIdentifier(
                suite.expectation_suite_name
            )

        context = GreatExpectationsDataValidator.get_data_context()
        sites = context.get_docs_sites_urls(identifier)
        for site in sites:
            url = site["site_url"]
            visualizations[url] = VisualizationType.HTML

        return visualizations

    def extract_metadata(
        self, data: Union[ExpectationSuite, CheckpointResult]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given Great Expectations object.

        Args:
            data: The Great Expectations object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        if isinstance(data, CheckpointResult):
            return {
                "checkpoint_result_name": data.name,
                "checkpoint_result_passed": data.success,
            }
        elif isinstance(data, ExpectationSuite):
            return {
                "expectation_suite_name": data.name,
            }
        return {}
