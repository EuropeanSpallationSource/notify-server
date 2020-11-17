import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


postgres_requires = ["psycopg2"]
requirements = [
    "alembic",
    "fastapi",
    "python-multipart",
    "httpx[http2]",
    "pyjwt",
    "cryptography",
    "ldap3",
    "sqlalchemy",
    "uvicorn[standard]",
    "gunicorn",
]
tests_requires = [
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "pytest-mock",
    "pytest-factoryboy",
    "requests",
    "respx",
]

setuptools.setup(
    name="ess-notify",
    description="ESS notification server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.esss.lu.se/ics-software/ess-notify-server",
    license="BSD-2 license",
    setup_requires=["setuptools_scm"],
    install_requires=requirements,
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
    ],
    extras_require={"postgres": postgres_requires, "tests": tests_requires},
    python_requires=">=3.8",
)
