"""CodePulse - Local-first code change intelligence and visualization platform."""

# Compatibility shim: Click 8.2+ requires ctx in Parameter.make_metavar(self, ctx),
# whereas Typer 0.15's rich formatting calls param.make_metavar() without arguments.
try:
    import click
    _orig_make_metavar = click.Parameter.make_metavar
    def _compat_make_metavar(self, ctx=None):
        try:
            return _orig_make_metavar(self, ctx)
        except TypeError:
            return _orig_make_metavar(self)
    click.Parameter.make_metavar = _compat_make_metavar
except Exception:
    pass

__version__ = "0.1.0"
