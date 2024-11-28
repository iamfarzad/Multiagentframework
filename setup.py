from setuptools import setup, find_packages

setup(
    name="multiagentframework",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "aiohttp>=3.8.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.20.0"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A multi-agent framework for code generation and review",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/multiagentframework",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 