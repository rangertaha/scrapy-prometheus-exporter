from setuptools import setup, find_packages


setup(
    name='scrapy-prometheus-exporter',
    version='1.0.1',
    url='https://github.com/rangertaha/scrapy-prometheus-exporter',
    description='Scrapy extension to export stats to Prometheus',
    author='rangertaha',
    author_email='rangertaha@gmail.com',
    license='MIT',
    packages=find_packages(exclude=('tests', 'tests.*')),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Framework :: Scrapy',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        'prometheus-client>=0.0.20'
        'Scrapy>=1.4.0',
    ],
)
