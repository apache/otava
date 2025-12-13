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

from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """Dynamically generate PyPI README by combining README.md and DISCLAIMER."""

    def update(self, metadata):
        """Called during build to update package metadata."""
        # Read README.md
        readme_path = Path(self.root) / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8")

        # Read DISCLAIMER
        disclaimer_path = Path(self.root) / "DISCLAIMER"
        disclaimer_content = disclaimer_path.read_text(encoding="utf-8")

        # Combine them
        combined_readme = f"{readme_content}\n## Disclaimer\n\n{disclaimer_content}"

        # Update metadata
        metadata["readme"] = {
            "content-type": "text/markdown",
            "text": combined_readme
        }
