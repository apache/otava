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
import json
import urllib
from datetime import datetime
from unittest.mock import patch

from otava.graphite import (
    Graphite,
    GraphiteConfig,
    GraphiteEvent,
    compress_target_paths,
)


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



def test_graphite_event_cleaning_and_datetime():
    event = GraphiteEvent(
        pub_time=1700000000,   # int timestamp
        version="0.1",
        branch="null",
        commit="",
    )

    assert isinstance(event.pub_time, datetime)
    assert event.pub_time.tzinfo is not None

    assert event.version == "0.1"
    assert event.branch is None
    assert event.commit is None

def test_graphite_event_dirty_data_handling():
    event = GraphiteEvent(
        pub_time="2024-01-01 10:00:00",
        version="null",
        branch="",
        commit=None,
    )

    assert event.version is None
    assert event.branch is None
    assert event.commit is None
    assert isinstance(event.pub_time, datetime)



class FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data


def test_fetch_events_parses_graphite_response():
    sample_data = [
        {
            "when": 1776526076,
            "what": "Performance Test",
            "data": "{'commit': 'p7q8r9', 'branch': 'new-feature', 'version': '0.0.1'}",
            "tags": ["perf-test", "daily", "my-product"],
            "id": 16,
        },
        {
            "when": 1776526136,
            "what": "Performance Test",
            "data": "{'commit': 'm4n5o6', 'branch': 'new-feature', 'version': '0.0.1'}",
            "tags": ["perf-test", "daily", "my-product"],
            "id": 17,
        },
    ]

    response_bytes = json.dumps(sample_data).encode("utf-8")

    def fake_urlopen(*args, **kwargs):
        return FakeResponse(response_bytes)

    with patch.object(urllib.request, "urlopen", fake_urlopen):
        g = Graphite(GraphiteConfig(url="http://graphite/"))

        events = g.fetch_events(tags=["perf-test"])

        assert len(events) == 2

        assert events[0].commit == "p7q8r9"
        assert events[0].branch == "new-feature"
        assert events[0].version == "0.0.1"

        assert events[1].commit == "m4n5o6"