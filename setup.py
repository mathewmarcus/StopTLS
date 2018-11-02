from setuptools import setup

setup(
    name="stoptls",
    version="0.1.0",
    packages=['stoptls'],
    description='MitM tool which performs opportunistic SSL/TLS stripping',
    author='Mathew Marcus',
    author_email='mathewmarcus456@gmail.com',
    long_description=open('README.md').read(),
    install_requires=[
        'aiohttp>=3.4.4',
        'beautifulsoup4>=4.6.3'
    ]
)
