import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


postgres_requires = ["psycopg2"]
requirements = [
    "alembic",
    "aiofiles",
    "cryptography",
    "fastapi",
    "pydantic>=2.0",
    "fastapi-versioning",
    "google-auth",
    "requests",
    "h2",
    "itsdangerous",
    "jinja2",
    "python-multipart",
    "httpx",
    "PyJWT",
    "ldap3",
    "SQLAlchemy<1.4",
    "uvicorn[standard]",
    "gunicorn",
    "sentry-sdk",
    "typer",
]
tests_requires = [
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "pytest-mock",
    "pytest-factoryboy",
    "respx",
    "Faker",
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={"console_scripts": ["notify-server=app.command:cli"]},
    extras_require={"postgres": postgres_requires, "tests": tests_requires},
    python_requires=">=3.8",
)
