import struct
from setuptools import Extension, find_packages, setup

from Cython.Build import cythonize

if struct.calcsize("P") * 8 != 64:
    raise RuntimeError(
        "Nebula Cython extension must be built with 64-bit Python."
    )


extensions = [
    Extension(
        "nebula.router",
        ["src/nebula/router.pyx"],
    ),
]


setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
        },
    ),
)
