from setuptools import find_packages, setup

setup(name='aws-ecs-remote',
      version='0.0.1',
      author='Ben Striner',
      url='https://github.com/bstriner/aws-ecs-remote',
      install_requires=[
          'boto3'
      ],
      packages=find_packages())

# python setup.py bdist_wheel sdist && twine upload dist\*
