from setuptools import setup

SRC_DIR = "enigma_docker_common"
PACKAGES = [SRC_DIR]

with open("README.md", "r") as fh:
    long_description = fh.read()

import os
thelibFolder = os.path.dirname(os.path.realpath(__file__))
requirementPath = thelibFolder + '/requirements.txt'
install_requires = [] # Examples: ["gunicorn", "docutils>=0.3", "lxml==0.5a7"]
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires = f.read().splitlines()

setup(
    name='enigma_docker_common',
    version='0.1.9',
    description='Scripts for Enigma Docker Images',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/enigmampc/docker-environment",
    author='Itzik Grossman',
    install_requires=install_requires,
    author_email='itzik@enigma.co',
    python_requires='>=3.6, <4',
    license='AGPL License',
    packages=PACKAGES,
    include_package_data=True,
    package_data={SRC_DIR: ['*.yaml']},
    classifiers=[
        'Programming Language :: Python',
    ]
)