from setuptools import setup


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="twitter_py", 
    version="0.1",
    packages=["twitter_py"],
    package_dir={"twitter_py": "."},
    install_requires=requirements,
)