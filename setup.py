from setuptools import find_packages, setup

setup(
    name="AppPilot",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["PyGObject>=3.8.0"],
    entry_points={"console_scripts": ["appilot=ubuntu_app_manager.app.main:main"]},
)
