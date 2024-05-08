import os
from pathlib import Path


def link_mirror(src: Path, dst: Path) -> None:
    """
    Creates a mirror of the source directory filled with symbolic links to the files. This function does not remove
    any files/directories that exist in `dst` if they dont exist in `src`.

    Parameters
    ----------
    src : Path
        The root directory to mirror
    dst : Path
        The root of the directory containing the links
    """

    src = src.resolve()
    dst = dst.resolve()

    for r, _, f in os.walk(src):
        for ff in f:
            link = Path(r.replace(str(src), str(dst))).joinpath(ff)
            file = Path(r).joinpath(ff)

            if not link.parent.exists():
                link.parent.mkdir(parents=True)

            link.symlink_to(file)
            print(f"{link} -> {file}")


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    link_mirror(src, dst)
