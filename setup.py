from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'django==6.1.0',
    'djangorestframework==3.18.0',
    'djangorestframework-simplejwt==5.5.1',
    'djangorestframework-camel-case==1.4.2',
    'drf-spectacular==0.30.0',
    'django-imagekit==6.1.0',
    'content-licencing',
    'anycluster',
    'rules==3.5',
    'django-el-pagination==4.1.2',
    'django-countries==9.0.0',
    'django-cors-headers==4.9.0',
    'Pillow',
    'matplotlib',
    'requests',
    'django-taggit==6.1.0', # used by app kit, potentiall used in the server in the future
    'google-cloud-vision',
    'django-rest-passwordreset==1.6.0',
    'fcm-django==3.2.*',
]

setup(
    name='localcosmos_server',
    version='1.1.3',
    description='LocalCosmos Private Server. Run your own server for localcosmos.org apps.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='The MIT License',
    platforms=['OS Independent'],
    keywords='django, localcosmos, localcosmos server, biodiversity',
    author='Thomas Uher',
    author_email='thomas.uher@code-for-nature.com',
    url='https://github.com/localcosmos/localcosmos-server',
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
