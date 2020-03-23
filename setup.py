from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'djangorestframework==3.11.0',
    'django-imagekit==4.0.2',
    'django-road',
    'content-licencing',
    'anycluster',
    'rules==2.1',
    'django-el-pagination==3.2.4',
    'django-octicons==1.0.2',
    'django-countries==5.5',
    'django-cors-headers==3.2.1',
    'Pillow',
]

setup(
    name='localcosmos_server',
    version='0.6.4',
    description='LocalCosmos Private Server. Run your own server for localcosmos.org apps.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='The MIT License',
    platforms=['OS Independent'],
    keywords='django, localcosmos, localcosmos server, biodiversity',
    author='Thomas Uher',
    author_email='thomas.uher@sisol-systems.com',
    url='https://github.com/SiSol-Systems/localcosmos-server',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    include_package_data=True,
    install_requires=install_requires,
)
