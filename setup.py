# -*- coding: utf-8 -*-

__author__ = "hitplum"

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='pyjsonpath',
      version='1.1.8',
      description='A Python toolkit for parsing JSON document',
      author='hitplum',
      author_email='ycx921101@163.com',
      url='https://github.com/hitplum/pyjsonpath',
      py_modules=["pyjsonpath"],
      # packages=['pyjsonpath'],
      # packages=find_packages(),
      long_description=long_description,
      long_description_content_type="text/markdown",
      license="MIT",
      classifiers=[
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: Implementation :: PyPy",
          "License :: OSI Approved :: MIT License",
      ],
      python_requires='>=3.5'
      )

