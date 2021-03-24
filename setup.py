import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


postgres_requires = ["psycopg2"]
requirements = [
    "alembic==1.5.7",
    "fastapi==0.61.2",
    "fastapi-versioning",
    "python-multipart==0.0.5",
    "h11==0.11.0",
    "h2==4.0.0",
    "hpack==4.0.0",
    "httpcore==0.12.1",
    "httptools==0.1.1",
    "httpx==0.16.1",
    "hyperframe==6.0.0",
    "PyJWT==2.0.0",
    "cryptography==3.2.1",
    "ldap3==2.8.1",
    "SQLAlchemy==1.3.20",
    "uvicorn[standard]",
    "gunicorn==20.0.4",
    "sentry-sdk==0.19.3",
]
tests_requires = [
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "pytest-mock",
    "pytest-factoryboy",
    "requests",
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
    ],
    extras_require={"postgres": postgres_requires, "tests": tests_requires},
    python_requires=">=3.8",
)
