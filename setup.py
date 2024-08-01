from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize("power_supply_experiment_c.pyx"))
