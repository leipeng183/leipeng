import os


class BadParameter(ValueError):
    pass


class ParamType(object):
    name = "value"

    def fail(self, value):
        raise BadParameter("Could not convert %r to %s" % (value, self.name))


class StringParamType(ParamType):
    name = "text"

    def convert(self, value, param=None, ctx=None):
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)


class IntParamType(ParamType):
    name = "integer"

    def convert(self, value, param=None, ctx=None):
        try:
            return int(value)
        except (TypeError, ValueError):
            self.fail(value)


class FloatParamType(ParamType):
    name = "float"

    def convert(self, value, param=None, ctx=None):
        try:
            return float(value)
        except (TypeError, ValueError):
            self.fail(value)


class BoolParamType(ParamType):
    name = "boolean"
    truth_map = {
        "1": True,
        "true": True,
        "t": True,
        "yes": True,
        "y": True,
        "on": True,
        "0": False,
        "false": False,
        "f": False,
        "no": False,
        "n": False,
        "off": False,
    }

    def convert(self, value, param=None, ctx=None):
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in self.truth_map:
            return self.truth_map[normalized]
        self.fail(value)


class FuncParamType(ParamType):
    def __init__(self, func):
        self.func = func
        self.name = getattr(func, "__name__", "value")

    def convert(self, value, param=None, ctx=None):
        try:
            return self.func(value)
        except (TypeError, ValueError):
            self.fail(value)


class Path(ParamType):
    name = "path"

    def __init__(self, exists=False, resolve_path=False):
        self.exists = exists
        self.resolve_path = resolve_path

    def convert(self, value, param=None, ctx=None):
        path = StringParamType().convert(value, param, ctx)
        if self.resolve_path:
            path = os.path.abspath(path)
        if self.exists and not os.path.exists(path):
            self.fail(value)
        return path


def convert_type(type=None, default=None):
    if hasattr(type, "convert"):
        return type

    if type is None and default is not None:
        type = default.__class__

    if type in (None, str):
        return StringParamType()
    if type is int:
        return IntParamType()
    if type is float:
        return FloatParamType()
    if type is bool:
        return BoolParamType()
    if callable(type):
        return FuncParamType(type)
    return type
