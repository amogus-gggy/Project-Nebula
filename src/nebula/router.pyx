# cython: language_level=3, boundscheck=False, wraparound=False

import re
from typing import Optional, Dict, Any, List, Tuple, Callable


# Type converters for path parameters
PATH_CONVERTERS = {
    "int": int,
    "float": float,
    "str": str,
    "path": lambda x: x,
}

# Compiled regex for parameter parsing
PARAM_PATTERN = re.compile(r"\{(\w+)(?::(\w+))?\}")


cdef class Router:
    """Fast path router implemented in Cython."""

    cdef:
        dict routes
        object _compiled_patterns

    def __init__(self):
        self.routes = {}
        self._compiled_patterns = {}

    cpdef add_route(self, str path, str method, object handler):
        """Add a route to the router."""
        cdef str path_key = path
        if path_key not in self.routes:
            self.routes[path_key] = {}
        self.routes[path_key][method.upper()] = handler

    cpdef tuple find_handler(self, str path, str method):
        """Find handler and path params for given path and method.

        Returns: (handler, path_params) or (None, None) if not found.
        """
        cdef:
            str method_upper = method.upper()
            dict methods
            object handler
            dict path_params

        # Exact match first (fastest path)
        if path in self.routes:
            methods = self.routes[path]
            if method_upper in methods:
                return (methods[method_upper], {})

        # Pattern match
        for route_path, methods in self.routes.items():
            path_params = self._match_path(route_path, path)
            if path_params is not None:
                if method_upper in methods:
                    return (methods[method_upper], path_params)

        return (None, None)

    cpdef dict _match_path(self, str pattern, str path):
        """Match path against pattern and extract typed parameters."""
        cdef:
            list pattern_parts = pattern.strip("/").split("/")
            list path_parts = path.strip("/").split("/")
            int i
            str pattern_part, path_part
            object match
            str param_name, param_type
            object converter

        if len(pattern_parts) != len(path_parts):
            return None

        path_params = {}

        for i in range(len(pattern_parts)):
            pattern_part = pattern_parts[i]
            path_part = path_parts[i]

            # Check if this is a parameter placeholder
            match = PARAM_PATTERN.match(pattern_part)
            if match:
                param_name = match.group(1)
                param_type = match.group(2) or "str"

                if param_type not in PATH_CONVERTERS:
                    raise ValueError(f"Unknown path type: {param_type}")

                converter = PATH_CONVERTERS[param_type]
                try:
                    path_params[param_name] = converter(path_part)
                except (ValueError, TypeError):
                    return None  # Type conversion failed
            elif pattern_part != path_part:
                return None  # Static parts don't match

        return path_params if path_params else None

    cpdef list get_routes(self):
        """Get all registered routes."""
        return list(self.routes.keys())
