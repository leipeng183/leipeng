import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from .types import BadParameter, Path, convert_type

__version__ = "0.0-local"


class ClickException(Exception):
    pass


class UsageError(ClickException):
    pass


class Context(object):
    def __init__(self, default_map=None):
        self.default_map = default_map or {}


class Option(object):
    def __init__(self, param_decls, type=None, default=None, multiple=False):
        self.param_decls = tuple(param_decls)
        self.type = convert_type(type, default)
        self.default = default
        self.multiple = multiple
        self.name = self._resolve_name(param_decls)
        self.flags = tuple(decl for decl in param_decls if isinstance(decl, str) and decl.startswith("-"))

    @staticmethod
    def _resolve_name(param_decls):
        explicit_name = None
        option_names = []
        for decl in param_decls:
            if not isinstance(decl, str):
                continue
            if decl.startswith("-"):
                option_names.append(decl)
            else:
                explicit_name = decl
        if explicit_name:
            return explicit_name
        long_options = [decl for decl in option_names if decl.startswith("--")]
        source = long_options[-1] if long_options else option_names[-1]
        return source.lstrip("-").replace("-", "_")

    def consume(self, token, args, index):
        if token not in self.flags:
            return False, index, None
        next_index = index + 1
        if next_index >= len(args):
            raise UsageError("Missing value for option %s" % token)
        value = self.type.convert(args[next_index], self, ctx=None)
        return True, next_index + 1, value


class Command(object):
    def __init__(self, callback, params=None, context_settings=None, pass_context=False):
        self.callback = callback
        self.params = list(params or [])
        self.context_settings = context_settings or {}
        self.pass_context = pass_context
        self.name = getattr(callback, "__name__", "command")
        self.__name__ = self.name
        self.__doc__ = getattr(callback, "__doc__", None)

    def make_context(self):
        return Context(default_map=self.context_settings.get("default_map") or {})

    def parse_args(self, args):
        args = list(args or [])
        parsed = {}
        index = 0
        while index < len(args):
            token = args[index]
            matched = False
            for option in self.params:
                matched, next_index, value = option.consume(token, args, index)
                if matched:
                    if option.multiple:
                        parsed.setdefault(option.name, []).append(value)
                    else:
                        parsed[option.name] = value
                    index = next_index
                    break
            if not matched:
                raise UsageError("Unknown option %s" % token)
        return parsed

    def resolve_kwargs(self, ctx, parsed):
        kwargs = {}
        default_map = ctx.default_map or {}
        for option in self.params:
            if option.name in parsed:
                value = parsed[option.name]
            elif option.name in default_map:
                value = default_map[option.name]
            else:
                value = option.default
            kwargs[option.name] = value
        return kwargs

    def invoke(self, args=None):
        ctx = self.make_context()
        parsed = self.parse_args(args or [])
        kwargs = self.resolve_kwargs(ctx, parsed)
        if self.pass_context:
            return self.callback(ctx, **kwargs)
        return self.callback(**kwargs)

    def main(self, args=None):
        return self.invoke(args=args)

    def __call__(self, *args, **kwargs):
        if args or kwargs:
            return self.callback(*args, **kwargs)
        return self.main(sys.argv[1:])


def command(name=None, context_settings=None):
    def decorator(func):
        params = getattr(func, "__click_params__", [])
        pass_ctx = getattr(func, "__click_pass_context__", False)
        cmd = Command(func, params=params, context_settings=context_settings,
                      pass_context=pass_ctx)
        if name:
            cmd.name = name
            cmd.__name__ = name
        return cmd
    return decorator


def option(*param_decls, **attrs):
    param = Option(param_decls, type=attrs.get("type"),
                   default=attrs.get("default"),
                   multiple=attrs.get("multiple", False))

    def decorator(func):
        params = list(getattr(func, "__click_params__", []))
        params.insert(0, param)
        func.__click_params__ = params
        return func
    return decorator


def pass_context(func):
    func.__click_pass_context__ = True
    return func


def echo(message=None, nl=True):
    text = "" if message is None else str(message)
    if nl:
        text += "\n"
    sys.stdout.write(text)


class Result(object):
    def __init__(self, output, exit_code, exception=None):
        self.output = output
        self.exit_code = exit_code
        self.exception = exception


class CliRunner(object):
    def invoke(self, cli, args=None):
        stdout = StringIO()
        exit_code = 0
        exception = None
        with redirect_stdout(stdout), redirect_stderr(stdout):
            try:
                if hasattr(cli, "main"):
                    cli.main(args=args or [])
                else:
                    cli(*(args or []))
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                exit_code = code
                exception = exc
            except Exception as exc:
                exit_code = 1
                exception = exc
        return Result(stdout.getvalue(), exit_code, exception)

    def isolated_filesystem(self):
        from .testing import isolated_filesystem
        return isolated_filesystem()
