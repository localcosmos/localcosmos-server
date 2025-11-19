from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'django==5.1.7',
    'djangorestframework==3.15.2',
    'djangorestframework-simplejwt==5.4.0',
    'djangorestframework-camel-case==1.4.2',
    'drf-spectacular==0.28.0',
    'django-imagekit==5.0.0',
    'content-licencing',
    'anycluster',
    'rules==3.5',
    'django-el-pagination==4.1.2',
    'django-octicons==1.0.2',
    'django-countries==7.6.1',
    'django-cors-headers==4.6.0',
    'Pillow',
    'matplotlib',
    'django-taggit==6.1.0',
    'requests',
]

setup(
    name='localcosmos_server',
    version='0.24.8',
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
