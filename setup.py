from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'django==4.1.*',
    'djangorestframework==3.14.0',
    'djangorestframework-simplejwt==5.2.*',
    'djangorestframework-camel-case==1.3.0',
    'drf-spectacular==0.24.*',
    'django-imagekit==4.1.*',
    'content-licencing',
    'anycluster',
    'rules==3.3',
    'django-el-pagination==3.3.0',
    'django-octicons==1.0.2',
    'django-countries==7.5',
    'django-cors-headers==3.13.0',
    'Pillow',
    'matplotlib',
    'django-taggit==3.1.0',
    'django-road',
]

setup(
    name='localcosmos_server',
    version='0.15.8',
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
