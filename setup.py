"""Setup script for cargo-doctor."""

from setuptools import setup, find_packages

setup(
    name="cargo-doctor",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "cargo-doctor=cargo_doctor.cli:main",
        ],
    },
)
