#!/bin/bash
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

# This is another script used by some project contributors to
# download and verify release tar files before voting to approve.
# You are encouraged to use one of these scripts to help you
# before voting. You may want to extend this script with your own
# checks, or use it as inspiration for your own script.

export DISTURL='https://dist.apache.org/repos/dist/dev'
export PROJECT=${1}
export ARTIFACT=${2}
export DISTRO=${DISTURL}/${PROJECT}/${ARTIFACT}

echo ${DISTRO}

export TMPDIR=/tmp/${PROJECT}

mkdir -p $TMPDIR
cd $TMPDIR
pwd

curl -f -L ${DISTRO} --output ${ARTIFACT}
curl -f -L ${DISTRO}.asc --output ${ARTIFACT}.asc
curl -f -L ${DISTRO}.sha256 --output ${ARTIFACT}.sha256
curl -f -L ${DISTRO}.sha512 --output ${ARTIFACT}.sha512

echo 'Check signature'
gpg --verify ${ARTIFACT}.asc
echo 'Compare checksum to sha256'
cat ${ARTIFACT}.sha256
shasum -a 256 ${ARTIFACT}
echo 'Compare checksum to sha512'
cat ${ARTIFACT}.sha512
shasum -a 512 ${ARTIFACT}
echo

