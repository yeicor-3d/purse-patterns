import inspect
import os
from typing import Callable
from build123d import *

# 3D printing basics
tol = 0.1 * MM  # Tolerance (tighter than usual)
wall_min = 0.4 * MM  # Minimum wall width
wall = 3 * wall_min  # Recommended width for most walls of this print
eps = 1e-5 * MM  # A small number


# Some common utilities

def show_all() -> Callable[[], None]:
    import ocp_vscode
    ocp_vscode.set_defaults(reset_camera=ocp_vscode.Camera.CENTER,
                            measure_tools=True, render_joints=True)
    return ocp_vscode.show_all


def caller_file() -> str:
    stack = inspect.stack()
    while 'global' in stack[0].filename:
        print(stack[0].filename)
        stack = stack[1:]
    print(stack[0].filename)
    return stack[0].filename


def export(part: Part) -> None:
    file_of_caller = caller_file()
    print("Exporting to STEP using ref %s" % file_of_caller)
    for i, solid in enumerate(part.solids()):
        if 'src/' in file_of_caller:
            file_in_build_dir = 'build/'.join(file_of_caller.rsplit('src/', 1))  # Last src/ -> build/
        else:
            file_in_build_dir = '../build/' + file_of_caller  # No src/ -> build/
        os.makedirs(os.path.dirname(file_in_build_dir), exist_ok=True)
        solid.export_step(file_in_build_dir[:-3] + (f'_{i}' if len(part.solids()) > 1 else '') + '.step')


def show_or_export(part: Part) -> None:
    try:
        show_all()()
    except Exception as e:
        print("Error showing part (%s), exporting to STEP instead" % e)
        export(part)


def bbox_to_box(bb: BoundBox) -> Box:
    return Box(bb.size.X, bb.size.Y, bb.size.Z, mode=Mode.PRIVATE).translate(bb.center())
