import struct
import atexit
import shutil
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

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

ROOT = Path(__file__).resolve().parent
CLEANUP_PATHS = [
    ROOT / "build",
    ROOT / "src" / "nebula.egg-info",
]


def _cleanup_build_artifacts() -> None:
    for path in CLEANUP_PATHS:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    for wheel_file in ROOT.glob("*.whl"):
        wheel_file.unlink(missing_ok=True)


atexit.register(_cleanup_build_artifacts)


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
