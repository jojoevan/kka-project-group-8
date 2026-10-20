"""Indonesian number formatting for everything a reader sees (figures, .md tables, docs): decimal
comma and dot thousands separator. CSV files keep the machine format (decimal point)."""
import math
import re

_SWAP = str.maketrans(".,", ",.")


def id_format(x, spec=""):
    """format(x, spec) with '.' and ',' swapped, e.g. id_format(9603.2, ",.0f") -> '9.603',
    id_format(0.005, "g") -> '0,005', id_format(5.974e-06, ".4g") -> '5,974e-06'."""
    return format(x, spec).translate(_SWAP)


def id_table_cell(v, floatfmt):
    """A .md table cell: floats in Indonesian format, NaN empty, everything else unchanged."""
    if isinstance(v, float):
        return "" if math.isnan(v) else id_format(v, floatfmt)
    return v


_CODE = re.compile(r"(`[^`]*`)")
_DECIMAL = re.compile(r"(?<![\w.,])(\d+)\.(\d+)(?=e[-+]?\d|(?!\w|\.\w))")


def id_text(text):
    """Decimal point -> decimal comma in generated prose/table text, leaving `code spans` untouched.
    Only numbers written by Python are expected here (no dot thousands separators)."""
    return "".join(part if part.startswith("`") else _DECIMAL.sub(r"\1,\2", part)
                   for part in _CODE.split(text))
