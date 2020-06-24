from distutils.core import setup

from setuptools import find_packages

setup(
    # Application name:
    name="DMSCftGenerator",
    version="1-0-0",
    author="DMS Automation",
    include_package_data=True,
    description="DMS Automation",
    install_requires=[
        "boto3",
    ],
)
