<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 -->

# Installation

## Install using pipx

Otava requires Python 3.8.  If you don't have python 3.8, use pyenv to install it.

Use pip to install otava:

```
pip install apache-otava
```

## Build Docker container

To build the Docker container, run the following command:

```bash
docker build -t otava .
```

> [!NOTE]
> The Dockerfile contains a `--mount` option that requires BuildKit [^1].
> The BuildKit can be installed with the following commands:
>
> Debian and Ubuntu: `apt install -y docker-buildx`
>
> Fedora: `dnf install docker-buildx`
>
> [^1]: https://docs.docker.com/go/buildkit/
