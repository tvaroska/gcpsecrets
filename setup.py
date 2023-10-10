# Copyright 2022 Google LLC.
# SPDX-License-Identifier: Apache-2.0

from setuptools import setup, find_packages

setup(
    name="GCPSecrets",
    version="0.0.1",
    author="Boris Tvaroska",
    author_email="tvaroska@google.com",
    description="Read GCP secrets as dictionary",
    packages=find_packages(),
    install_requires=["google-cloud-secret-manager>=2.10"],
)
