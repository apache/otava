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

from otava.graphite import compress_target_paths


def test_compress_target_paths():
    paths = [
        "foo.bar.p50",
        "foo.bar.p75",
        "foo.bar.p99",
        "foo.foo.baz.p50",
        "foo.foo.baz.p75",
        "foo.foo.baz.throughput",
        "something.else",
    ]

    assert set(compress_target_paths(paths)) == {
        "foo.bar.{p50,p75,p99}",
        "foo.foo.baz.{p50,p75,throughput}",
        "something.else",
    }
