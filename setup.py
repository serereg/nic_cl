from setuptools import setup, find_packages
from pathlib import Path


def read_requirements(name: str):
    p = Path(name).parent.joinpath(name)
    reqs = [line for line in p.read_text().splitlines() if line]
    return reqs


setup(
    name="pargolovo-server",
    version="0.0.1",
    packages=find_packages(),
    install_requires=read_requirements("requirements.txt"),
)
