import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eventeditor",
    version="1.0.2",
    author="leoetlino",
    author_email="leo@leolam.fr",
    description="Event editor for Breath of the Wild",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leoetlino/event-editor",
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
    ],
    include_package_data=True,
    install_requires=['evfl>=0.11.1', 'PyYAML~=3.12'],
    python_requires='>=3.6',
    entry_points={
        'gui_scripts': [
            'eventeditor = eventeditor.__main__:main'
        ],
    },
)
