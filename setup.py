import os
from os.path import exists, join
from setuptools import find_packages, setup

base_dir = os.path.dirname(__file__)
readme_path = join(base_dir, "README.md")
if exists(readme_path):
    with open(readme_path) as stream:
        long_description = stream.read()
else:
    long_description = ""

INSTALL_REQUIRES = ["django>=3.0<4"]
DEV_REQUIRES = ("black", "flake8", "pytest", "pytest-django", "factory_boy", "ipdb", "setuptools_scm", "tox")


setup(
    name="django-orm-plus",
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(
        dev=DEV_REQUIRES,
    ),
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="Make efficient and explicit SQL queries with the Django ORM automatically",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Josh",
    url="https://github.com/lime-green/django-orm-plus",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6, <4",
    license="MIT",
    keywords=["django", "ORM", "SQL", "development"],
)
