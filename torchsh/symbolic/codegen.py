from typing import Callable
import torch
from .rsh import Ylm

try:
    import sympy as sym
except ImportError:
    raise Exception(
        "Failed to import sympy\n. You need `pip install sympy` for this part of the"
        " code."
    )


x, y, z = sym.symbols("x:z", real=True)

_subs = {
    x**2: sym.symbols("x2"),
    y**2: sym.symbols("y2"),
    z**2: sym.symbols("z2"),
    x * y: sym.symbols("xy"),
    x * z: sym.symbols("xz"),
    y * z: sym.symbols("yz"),
}

header_tpl = r"""
'''Real spherical harmonics in Cartesian form for PyTorch.

This is an autogenerated file. See
https://github.com/cheind/torch-spherical-harmonics
for more information.
'''
"""

import_tpl = r"""
import torch
"""


method_tpl = r"""
def rsh_cart_{degree}(xyz:torch.Tensor):
    '''Computes all real spherical harmonics up to {degree} degree.

    This is an autogenerated method. See
    https://github.com/cheind/torch-spherical-harmonics
    for more information.

    Params:
        xyz: (N,...,3) tensor of points on the unit sphere
    
    Returns:
        rsh: (N,...,K) real spherical harmonics projections of input.
    '''

    x = xyz[...,0]
    y = xyz[...,1]
    z = xyz[...,2]

    x2=x**2
    y2=y**2
    z2=z**2
    xy=x*y
    xz=x*z
    yz=y*z

    return torch.stack(
        [{ynms}]
        ,-1
    )    
"""


def _substitute(f: sym.Expr) -> sym.Expr:
    """Substitutes pre-computed values of spherical harmonics"""
    return f.subs(_subs)


def generate_ynm_instructions(
    max_degree: int = 5, start_degree: int = 0
) -> list[list[str]]:
    """Generates PyTorch instructions for Ynm up to degree max_degree exclusive-"""
    ynms = []
    for n in range(start_degree, max_degree):
        level = []
        for m in range(-n, n + 1):
            ylm = Ylm(n, m, x, y, z)
            ylmstr = sym.pycode(_substitute(sym.N(ylm)))
            if n == 0:
                ylmstr = f"xyz.new_tensor({ylmstr}).expand(xyz.shape[:-1])"
            level.append(ylmstr)
        ynms.append(level)
    return ynms


def generate_ynm_method(ynm_instr: list[list[int]], degree: int) -> str:
    """Returns the source code for `rsh_cart` method defined up to given degree."""

    ynms = [item for sublist in ynm_instr[:degree] for item in sublist]

    return method_tpl.format(degree=degree, ynms=",".join(ynms))


def generate_ynm_file(ynm_instr: list[list[int]], degrees: list[int]) -> str:
    """Returns the source code for `rsh_cart` method defined up to given degree."""

    content_parts = [header_tpl, import_tpl]
    for d in degrees:
        content_parts.append(generate_ynm_method(ynm_instr, degree=d))

    return "\n".join(content_parts)


def compile_file(degree: int) -> Callable[[torch.Tensor], torch.Tensor]:
    instr = generate_ynm_instructions(max_degree=degree + 1)
    source = generate_ynm_file(instr, degrees=[degree])
    ctx = {}
    exec(source, ctx)
    return ctx[f"rsh_cart_{degree}"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. If not given, prints to stdout",
        default=None,
    )
    parser.add_argument("-n", "--degree", help="Maximum degree to generate", default=4)
    args = parser.parse_args()

    instr = generate_ynm_instructions(max_degree=8, start_degree=0)
    file = generate_ynm_file(instr, [2, 4, 8])

    import black

    mode = black.FileMode()
    fast = False
    fmt_file = black.format_file_contents(file, fast=fast, mode=mode)

    if args.output:
        with open(args.output, "w") as f:
            f.write(fmt_file)
    else:
        print(fmt_file)
