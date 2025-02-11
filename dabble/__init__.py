""" Builds membrane protein systems """

__version__ = '2.7.12'
__author__ = 'Robin Betz'

import sys
import inspect

#=========================================================================

# Currently supported output formats and description
supported_formats = {
    "amber": ".prmtop and .inpcrd Amber PARM7 and RST7 formats",
    "charmm": ".psf and .pdb Protein Structure File and PDB coordinates",
    "desmond": "",
    "gromacs": ".top and .gro GROMACS topology and coordinate files",
    "lammps": ".dat file suitable for input to LAMMPS",
    "mae": ".mae structure file, no parameters or atom types",
    "pdb": "Protein Data Bank PDB file. Will not contain explicit bonds."
}

#=========================================================================

class DabbleError(Exception):
    """
    An error message aimed at users, without a really long traceback.
    """

    def __init__(self, msg):
        super(DabbleError, self).__init__()
        try:
            ln = sys.exc_info()[-1].tb_lineno
        except AttributeError:
            ln = inspect.currentframe().f_back.f_lineno

        print("\n\n\n{0.__name__} (line {1}): {2}\n".format(type(self), ln, msg))

#=========================================================================

from dabble.builder import DabbleBuilder
from dabble.fileutils import *
from dabble.vmdsilencer import VmdSilencer

#=========================================================================
