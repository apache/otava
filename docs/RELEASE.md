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

# Creating Apache Otava Release

> [!TIP]
> This document is based on the release guide of [Apache Flink project](https://cwiki.apache.org/confluence/display/FLINK/Creating+a+Flink+Release).

## Introduction

The Otava community treats releases with great importance. They are a public face of the project and most users interact with the project only through the releases. Releases are signed off by the entire Otava community in a public vote.

Each release is executed by a Release Manager, who is selected/proposed by the Otava PMC members. This document describes the process that the Release Manager follows to perform a release. Any changes to this process should be discussed and adopted on the [dev@otava.apache.org](mailto:dev@otava.apache.org) mailing list.

Please remember, that the act of publishing software has both legal and policy significance. This guide complements the foundation-wide

* [Product Release Policy](https://www.apache.org/dev/release.html),
* [Release Distribution Policy](https://infra.apache.org/release-distribution.html),and
* [Release Download Pages for Projects](https://infra.apache.org/release-download-pages.html)

## Overview

### What is in Apache Otava Release

Apache Otava release consists of:
* ASF source zips archived on [dist.apache.org](dist.apache.org).
* PyPI wheels published to [pypi.org](https://pypi.org/project/apache-otava/).
* Docker images published to [Dockerhub](https://hub.docker.com/r/apache/otava).
* Release tag on [GitHub](https://github.com/apache/otava/releases).
* All of the above published on [https://otava.apache.org/docs/downloads](https://infra.apache.org/release-download-pages.html)
* ...and on dev@otava.apache.org and general@incubator.org

### Phases of the release

The release process consists of several steps:
1. Decide to release
2. Prepare for the release
3. Build a release candidate
4. Vote on the release candidate:
- While we are in the ASF incubator program, voting has 2 phases: On the Otava project mailing list, then formally on the Incubator project list.
5. If necessary, fix any issues and go back to step 3.
6. Finalize the release
7. Promote the release

## Decide to release

Deciding to release and selecting a Release Manager is the first step of the release process. This is a consensus-based decision of the entire community.
Anybody can propose a release on the dev@ mailing list, giving a solid argument and nominating a committer as the Release Manager (including themselves). There’s no formal process, no vote requirements, and no timing requirements. Any objections should be resolved by consensus before starting the release.
In general, the community prefers to have a rotating set of 3-5 Release Managers. Keeping a small core set of managers allows enough people to build expertise in this area and improve processes over time, without Release Managers needing to re-learn the processes for each release. That said, if you are a committer interested in serving the community in this way, please reach out to the community on the dev@ mailing list.

#### Checklist to proceed to the next step

1. Community agrees to release
2. Community selects a Release Manager

## Prepare for the release

Before your first release, you should perform one-time configuration steps. This will set up your security keys for signing the release and access to various release repositories.

## Paths

For clarity, we will use the following environment variables when referring to different paths and repositories. You are free to use any path you desire for the values of these repositories:

```bash
# This is the main development repository, that you cloned from github.com/apache/otava
export OTAVA_GIT_REPO=$HOME/git/apache/otava

# This is an ASF subversion repository where you can publish preview/release candidate packages before the vote
# https://dist.apache.org/repos/dist/dev/incubator/otava/
export OTAVA_SVN_DEV=$HOME/svn/apache/otava-dist-dev-repo

# This is an ASF subversion repository where you publish the tar files, images, etc. after the vote
# https://dist.apache.org/repos/dist/release/incubator/otava/
export OTAVA_SVN_REL=$HOME/svn/apache/otava-dist-release-repo
```

While at it, make sure the paths exist.

```bash
mkdir -p dirname $OTAVA_GIT_REPO
mkdir -p dirname $OTAVA_SVN_DEV
mkdir -p dirname $OTAVA_SVN_REL
```


### One-time configuration

#### GPG Key

You need to have a GPG key to sign the release artifacts. Please be aware of the ASF-wide [release signing guidelines](https://www.apache.org/dev/release-signing.html). If you don’t have a GPG key associated with your Apache account, please create one according to the guidelines.
Determine your Apache GPG Key and Key ID, as follows:

```bash
gpg --list-keys
```

This will list your GPG keys. One of these should reflect your Apache account, for example:

```bash
--------------------------------------------------
pub   2048R/845E6689 2016-02-23
uid                  Nomen Nescio <anonymous@apache.org>
sub   2048R/BA4D50BE 2016-02-23
```

Here, the key ID is the 8-digit hex string in the pub line: 845E6689.
Now, add your Apache GPG key to the Otava's KEYS file in the [release](https://dist.apache.org/repos/dist/release/incubator/otava/KEYS) repository at [dist.apache.org](https://dist.apache.org/repos/dist/). Follow the instructions listed at the top of these files. (Note: Only PMC members have write access to the release repository. If you end up getting 403 errors ask on the mailing list for assistance.) PMC members can refer to the following scripts to add your Apache GPG key to the KEYS in the release repository.

```bash
# Checkout both the dev and release repositories up front
svn co https://dist.apache.org/repos/dist/dev/incubator/otava $OTAVA_SVN_DEV
svn co https://dist.apache.org/repos/dist/release/incubator/otava $OTAVA_SVN_REL

# For GPG key we always use the dist/release repo:
cd $OTAVA_SVN_REL
(gpg --list-sigs <YOUR_KEY_ID> && gpg --armor --export <YOUR_KEY_ID>) >> KEYS
svn ci -m "[otava] Add <YOUR_NAME>'s public key"
```

*NOTE: Never remove keys from the above file, if they have been used to sign a release. This is true even for expired keys.*

Configure git to use this key when signing code by giving it your key ID, as follows:

```bash
git config --global user.signingkey 845E6689
```

You may drop the `--global` option if you’d prefer to use this key for the current repository only.
You may wish to start `gpg-agent` to unlock your GPG key only once using your passphrase. Otherwise, you may need to enter this passphrase hundreds of times. The setup for gpg-agent varies based on operating system, but may be something like this:

```
eval $(gpg-agent --daemon --no-grab --write-env-file $HOME/.gpg-agent-info)
export GPG_TTY=$(tty)
export GPG_AGENT_INFO
```

#### PyPI

Create both [PyPI](https://pypi.org/) and [TestPyPI](https://test.pypi.org) accounts. Then, ask PMC members to get added to [Otava](https://pypi.org/org/apache-otava/) organization on both platforms.

Install `twine` if you don't have it already:

```bash
$ pip install twine
```

#### Dockerhub

Make sure you have a Dockerhub account.
Create ASF INFRA issue to add your Dockerhub account to `apache` organization, `otava` team.

### Checklist to proceed to the next step

1. Release Manager’s GPG key is published to dist.apache.org
2. Release Manager’s GPG key is configured in git configuration
3. Release Manager's GPG key is configured as the default gpg key. 
4. Release Manager's PyPI and TestPyPI accounts are created and have access to `apache-otava` organizations on both platforms.
5. Release Manager's Dockerhub account is created and has write access to `apache/otava` repository.


## Build a release candidate

The core of the release process is the build-vote-fix cycle. Each cycle produces one release candidate. The Release Manager repeats this cycle until the community approves one release candidate, which is then finalized.

### Set up ENV variables for convenience

```bash
export RELEASE_VERSION=...
export RELEASE_CANDIDATE=rc...

# And the repository paths from above
export OTAVA_GIT_REPO=
export OTAVA_SVN_DEV=
export OTAVA_SVN_REL=

```

For example,

```bash
export RELEASE_VERSION=0.7.0
export RELEASE_CANDIDATE=rc1
...
```

### Create the release commit

Open  `/docs/release-notes/$RELEASE_VERSION-incubating` in your favorite text editor.
Draft and save the release notes. You can use the following template:

```
# $RELEASE_VERSION-incubating

Write a few sentences that highlight the main feature(s) in this release.

Call out backward incompatible changes, known issues, or anything users have to take into account when upgrading.

Go to https://github.com/apache/otava/compare/$PREVIOUS_RELEASE_VERSION-incubating...$RELEASE_VERSION-incubating
to generate the list of all commits between this release and the previous. Copy the list here, and delete small
or low impact commmits. Leave the summary list of changes here.

To view the full list of new features, bug fixes and other commits in this release, please go to https://github.com/apache/otava/compare/$PREVIOUS_RELEASE_VERSION-incubating...$RELEASE_VERSION-incubating
```

Check /pyproject.toml, it should have a line:

```
version = $RELEASE_VERSION
```

IMPORTANT: Note that above the pyproject version and the release-notes file are already set to $RELEASE_VERSION-incubating, but below tag and commit message will be $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE. If there are several release candidates, you should edit/add to the same release-notes file as above. (This is git, after all...) The commit message on the other hand should use @RELEASE_VERSION-incubating-$RELEASE_CANDIDATE and if there are more than one candidate and vote, then the following commit and tag increase by 1.

```bash
git tag -a $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE -m "$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE"
git push origin $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE
```

### Download sources from Github

```bash
mkdir -p release
wget -O release/apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz https://github.com/apache/otava/archive/refs/tags/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE.tar.gz
```

### Build PyPI artifacts

```bash
uv build --no-create-gitignore
mv dist release/pypi
```

### Create and verify signatures

Sign and verify signatures for source release candidate:

```bash
cd release
gpg --armor --output apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz.asc --detach-sig apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz
gpg --verify apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz.asc apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz
```

Sign and verify signatures for PyPI artifacts:

```bash
cd pypi
gpg --armor --output apache_otava-$RELEASE_VERSION-py3-none-any.whl.asc --detach-sig apache_otava-$RELEASE_VERSION-py3-none-any.whl
gpg --armor --output apache_otava-$RELEASE_VERSION.tar.gz.asc --detach-sig apache_otava-$RELEASE_VERSION.tar.gz

gpg --verify apache_otava-$RELEASE_VERSION-py3-none-any.whl.asc apache_otava-$RELEASE_VERSION-py3-none-any.whl
gpg --verify apache_otava-$RELEASE_VERSION.tar.gz.asc apache_otava-$RELEASE_VERSION.tar.gz
```

### Create and verify checksums

Create and verify checksum for source release candidate:

```bash
cd release
sha512sum apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz > apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz.sha512

sha512sum --check apache-otava-$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE-src.tar.gz.sha512
```

Create and verify checksums for PyPI artifacts:

```bash
cd pypi
sha512sum apache_otava-$RELEASE_VERSION-py3-none-any.whl > apache_otava-$RELEASE_VERSION-py3-none-any.whl.sha512
sha512sum apache_otava-$RELEASE_VERSION.tar.gz > apache_otava-$RELEASE_VERSION.tar.gz.sha512

sha512sum --check apache_otava-$RELEASE_VERSION.tar.gz.sha512
sha512sum --check apache_otava-$RELEASE_VERSION-py3-none-any.whl.sha512
```

### Publish Release Candidate

```bash
cp -r release $OTAVA_SVN_DEV/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE
cd $OTAVA_SVN_DEV
svn update && svn status

svn add $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/
svn ci -m "[otava] Upload $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE for review and voting"
```

### Publish PyPI artifacts on test.pypi.org

In svn dev/preview directory:

```bash
# Go to dev/preview svn directory
cd $OTAVA_SVN_DEV
cd  $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/pypi
# Publish to Test PyPI
twine upload --verbose --repository testpypi apache_otava-$RELEASE_VERSION-py3-none-any.whl apache_otava-$RELEASE_VERSION.tar.gz
# Verify at https://test.pypi.org/project/apache-otava/
```


## Vote on the release candidate

Once you have built and individually reviewed the release candidate, please share it for the community-wide review. Please review foundation-wide [voting guidelines](https://www.apache.org/foundation/voting.html) for more information.

### Start a vote on the project mailing list

Mailing list: [dev@otava.apache.org](mailto:dev@otava.apache.org)
Subject: `[VOTE] Release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE`
Here is a text template, please adjust as you see fit:

```
Hello everyone,

Please review and vote for the releasing Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE.

Release notes for this release candidate
https://github.com/apache/otava/blob/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/docs/release-notes/$RELEASE_VERSION-incubating

The official ASF source release has been deployed to https://dist.apache.org/repos/dist/dev/incubator/otava/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/.
GH tag for release https://github.com/apache/otava/releases/tag/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE.
The release has been signed with a key <your-signature> available here https://downloads.apache.org/incubator/otava/KEYS.

Please download, verify, and test.

Please vote on releasing this candidate by replying with:
[ ] +1 Release this package
[ ] 0 No opinion
[ ] -1 Do not release (please provide reason)

To learn more about Apache Otava, please see https://otava.apache.org.

This vote will be open for at least 72 hours.

Checklist for reference:
[ ] Download links are valid.
[ ] Checksums and signatures.
[ ] LICENSE/NOTICE files exist.
[ ] No unexpected binary files.
[ ] All source files have ASF headers.
[ ] Can install from source.
[ ] Can run examples using all supported Python versions.
```

**If there are any issues found in the release candidate, reply on the vote thread to cancel the vote.** There’s no need to wait 72 hours. Proceed to the [In case project or Incubator vote fails...](RELEASE.md#in-case-project-or-incubator-vote-fails) section below and address the problem. However, some issues don’t require cancellation. For example, if an issue is found in the website pull request, just correct it on the spot and the vote can continue as-is.

For cancelling a release, the release manager needs to send an email to the release candidate thread, stating that the release candidate is officially cancelled. Next, all artifacts created specifically for the RC in the previous steps need to be removed:
- Delete the staging repository in Nexus
- Remove the source / binary RC files from dist.apache.org
- Delete the source code tag in git

**If there are no issues**, reply on the vote thread to close the voting. Then, tally the votes in a separate email. Here’s an email template; please adjust as you see fit:

Mailing list: dev@otava.apache.org
Subject: `[RESULT][VOTE] Release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE`
Text:

```
Hey everyone,

The vote to release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE has passed with X +1 binding votes, Y +1 non-binding votes and 0 -1 votes.
Vote thread: <link-to-vote-thread-archive>.
```

### In case project or Incubator vote fails...

1. Create a result thread on the corresponding mailing list.

Subject: `[RESULT][VOTE] Release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE`
Sample text:

```
Hey everyone,

The vote to release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE has failed with X -1 binding votes.

Vote thread: <link-to-vote-thread-archive>.
```

2. Fix the issue.
3. Increment `RELEASE_CANDIDATE` env variable.
4. Repeat the steps above.

### Start a vote on the Incubator mailing list

After the project vote passes, start a vote on the Incubator mailing list.

Mailing list: [general@incubator.apache.org](mailto:general@incubator.apache.org)
Subject: `[VOTE] Release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE`
Text template, please adjust as you see fit:

```
Hello,

This is a call for a vote to release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE.

The vote thread: <link-to-the-project-vote-thread>
Vote result: <link-to-the-project-vote-result-thread>
Release candidate: https://dist.apache.org/repos/dist/dev/incubator/otava/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/
GH tag for release https://github.com/apache/otava/releases/tag/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE.
Release notes: https://github.com/apache/otava/blob/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE/docs/release-notes/$RELEASE_VERSION-incubating

The release has been signed with Key <your-signature>, corresponding to <your-apache-email> available here https://downloads.apache.org/incubator/otava/KEYS.

This vote will be open for at least 72 hours.

Checklist for reference:

[ ] Download links are valid.
[ ] Checksums and signatures.
[ ] LICENSE/NOTICE files exist
[ ] No unexpected binary files
[ ] All source files have ASF headers
[ ] Can install from source 
[ ] Can run examples using all supported Python versions

To learn more about Apache Otava, please see https://otava.apache.org.
```

### Create Incubator vote result thread

Proceed only after Incubator vote succeeds. If the vote failed, see section [In case project or Incubator vote fails...](RELEASE.md#in-case-project-or-incubator-vote-fails) above.

Mailing list: [general@incubator.apache.org](mailto:general@incubator.apache.org)
Subject: `[RESULT][VOTE] Release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE`
Sample text:

```
Hello everyone,

The vote to release Apache Otava (incubating) $RELEASE_VERSION-$RELEASE_CANDIDATE has passed with X +1
binding and Y +1 non-binding votes, no -1 votes.

Binding +1 votes:
- ...
- ...

Non-Binding +1 votes:
- ...

Vote thread: <link-to-vote-thread>

We will proceed with publishing the approved artifacts and sending out the announcement soon.
```

## Finalize the release

Once the release candidate has been reviewed and approved by the project and Incubator community, the release should be finalized. This involves the final deployment of the release candidate to the release repositories, merging of the website changes, etc.

### Publish Source Release

```bash
svn mv https://dist.apache.org/repos/dist/dev/incubator/otava/$RELEASE_VERSION-incubating-$RELEASE_CANDIDATE https://dist.apache.org/repos/dist/release/incubator/otava/$RELEASE_VERSION-incubating -m "[otava] Release $RELEASE_VERSION-incubating artifacts"
```

### Publish release tag on Github

```bash
git checkout $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE
git tag -a $RELEASE_VERSION-incubating -m "$RELEASE_VERSION-incubating"
git push origin $RELEASE_VERSION-incubating
```

Go to the [Github releases page](https://github.com/apache/otava/releases) and
click on `Draft a new release` and select the tag `$RELEASE_VERSION-incubating`.

Copy paste the release announcement and changelog from `$OTAVA_GIT_REPO/docs/release-notes` and publish the release.

### Update the website download page

Update the list of releases on the website at https://otava.apache.org/docs/download to include the new release.

**Congratulations! You have now completed the official ASF release, which is the source release.**

But there is more...

### Publish PyPI artifacts

In svn release directory:


```bash
# Go to release pypi directory
cd $OTAVA_SVN_REL
svn update && svn status

cd  $RELEASE_VERSION-incubating/pypi

twine upload --verbose  apache_otava-$RELEASE_VERSION-py3-none-any.whl apache_otava-$RELEASE_VERSION.tar.gz
# Verify at https://pypi.org/project/apache-otava/
```

### Publish Docker Image

Ensure you have a multi-platform builder set up:

```bash
docker buildx create --name multiplatform --use || docker buildx use multiplatform
```

Log in to Dockerhub and build and push the multi-platform image:

```bash
docker login
RELEASE_VERSION=$RELEASE_VERSION-incubating uv run tox -e docker-push
```

### Remove old release candidates from dist.apache.org

In `otava-dist-release-repo`:

```bash
cd $OTAVA_SVN_REL
svn update && svn status
svn rm $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE
svn ci -m "[otava] Remove $RELEASE_VERSION-incubating-$RELEASE_CANDIDATE"
```

## Promote the release

Once the release has been finalized, the last step of the process is to promote the release within the project and beyond. Please wait for 1 hour after finalizing the release in accordance with the [ASF release policy](https://www.apache.org/legal/release-policy.html#release-announcements).

### Send announcement email to project and incubator mailing lists

Mailing lists:
- [general@incubator.apache.org](mailto:general@incubator.apache.org)
- [dev@otava.apache.org](mailto:dev@otava.apache.org)

Subject: `[ANNOUNCE] Apache Otava (incubating) version $RELEASE_VERSION released`
Text template:

```
Apache Otava (incubating) version $RELEASE_VERSION has been released.

Apache Otava is a command-line tool that detects and alerts about statistically significant changes in performance test results (more generally, time-series data) stored in CSV files or a number of supported databases.

A typical use-case of Otava is as follows:
1. A set of performance tests is scheduled repeatedly, such as after each commit is pushed.
2. The resulting metrics of the test runs are stored in a time series database (Graphite) or appended to CSV files.
3. Otava is launched by a Jenkins/Cron job (or an operator) to analyze the recorded metrics regularly.
4. Otava notifies about significant changes in recorded metrics by outputting text reports or sending Slack notifications.
5. Otava is capable of finding even small, but persistent shifts in metric values, despite noise in data. It adapts automatically to the level of noise in data and tries to notify only about persistent, statistically significant changes, be it in the system under test or in the environment.

Highlights of $RELEASE_VERSION release are:
- ...
- ...

$RELEASE_VERSION is available as:
- Source release https://otava.apache.org/docs/download
- Github release https://github.com/apache/otava/releases/
- PyPI https://pypi.org/project/apache-otava/
- Docker image https://hub.docker.com/r/apache/otava

Otava resources:
- Website: https://otava.apache.org/
- Issues: https://github.com/apache/otava/issues
- Mailing list: dev@otava.apache.org

<Your name>
On behalf of Apache Otava (incubating) Team
```

### Social Media

Tweet, post on Facebook, LinkedIn, and other platforms. Ask other contributors to do the same.

## Improve the process

It is important that we improve the release processes over time. Once you’ve finished the release, please take a step back and look what areas of this process and be improved. Perhaps some part of the process can be simplified. Perhaps parts of this guide can be clarified.

If we have specific ideas, please start a discussion on the dev@ mailing list and/or propose a pull request to update this guide.
