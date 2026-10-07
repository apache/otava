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

import pytest

from otava.attributes import form_hyperlink_html_str, get_back_links


@pytest.mark.parametrize("scheme", ["http", "https", "ssh", "git+ssh", "HTTPS", "SSH"])
def test_hyperlink_allows_safe_schemes_and_protects_new_window(scheme):
    url = f"{scheme}://example.com/repo?a=1&b=2"
    html = form_hyperlink_html_str("<Test>", url)
    assert html == (
        f'<li><a href="{scheme}://example.com/repo?a=1&amp;b=2" '
        'target="_blank" rel="noopener noreferrer">&lt;Test&gt;</a></li>'
    )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        " \tjavascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "ftp://example.com/repo",
        "//example.com/repo",
        "/relative/path",
        "https://[invalid",
        "",
    ],
)
def test_hyperlink_omits_unsafe_or_invalid_urls(url):
    assert form_hyperlink_html_str("Test", url) == ""


@pytest.mark.parametrize(
    "attributes",
    [
        {"test_url": "javascript:alert(1)"},
        {"run_url": "javascript:alert(1)"},
        {"repo_url": "javascript:alert(1)", "commit": "abc123"},
        {"repo_url": "javascript:alert(1)", "branch": "main"},
    ],
)
def test_back_links_omit_unsafe_urls(attributes):
    html = get_back_links(attributes)
    assert "<a " not in html
    assert "Created by Otava:" in html


@pytest.mark.parametrize("scheme", ["http", "https", "ssh", "git+ssh"])
@pytest.mark.parametrize("ref, path", [("commit", "commit/abc123"), ("branch", "tree/abc123")])
def test_back_links_preserve_repository_url_schemes(scheme, ref, path):
    html = get_back_links({"repo_url": f"{scheme}://example.com/repo", ref: "abc123"})
    assert f'href="{scheme}://example.com/repo/{path}"' in html
    assert 'rel="noopener noreferrer"' in html
