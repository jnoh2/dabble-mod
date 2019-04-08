"""
This module contains the MoleculeWriter class. It is used to apply
atom names from known topologies to the molecule by using a graph-based
representation of each molecule.

Author: Robin Betz

Copyright (C) 2019 Robin Betz
"""

# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330
# Boston, MA 02111-1307, USA.


from __future__ import print_function
import logging

from networkx.algorithms import isomorphism
from vmd import atomsel

logger = logging.getLogger(__name__) # pylint: disable=invalid-name

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                                   CLASSES                                   #
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class MoleculeWriter(object):
    """
    Represents a writer that will parameterize built systems into input files
    for some simulation program.

    Attributes:
        molid (int): VMD molecule ID to write
        output_prefix (str): Prefix for output file names. Appropriate suffix
            will be added depending on the file type.
    """

    #==========================================================================

    def __init__(self, molid, **kwargs):
        """
        Creates a molecule writer

        Args:
            molid (int): VMD molecule ID of system to write
            tmp_dir (str): Directory for temporary files. Defaults to "."
            lipid_sel (str): Lipid selection string. Defaults to "lipid"

            extra_topos (list of str): Additional topology (.str, .off, .lib) to
                include.
            extra_params (list of str): Additional parameter sets (.str, .frcmod)
            debug_verbose (bool): Prints additional output, like from tleap.
        """
        self.molid = molid

        self.tmp_dir = kwargs.get("tmp_dir", ".")
        self.lipid_sel = kwargs.get("lipid_sel", "lipid")
        self.debug_verbose = kwargs.get("debug_verbose", False)

    #==========================================================================

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #                            STATIC FUNCTIONS                             #
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    @staticmethod
    def get_pdb_line(atom, index, resindex, hetatom=False):
        """
        Get the PDB-formatted line corresponding to this atom, with a newline
        at the end.

        Args:
            atom (VMD atomsel): Atom selected
            index (int): Index in PDB file.
            resindex (int): Residue number in PDB file
            hetatom (bool): If this is part of a non-standard residue

        Returns:
            (str) PDB file line for this atom
        """
        if len(atom) != 1:
            raise ValueError("PDB entry selection must be only one atom")

        ins = atom.insertion[0]
        result = "%-6s%5d %-5s%-4s%c%4d%c  %8.3f%8.3f%8.3f%6.2f%6.2f" \
                 "     %-4s%2s\n" % ("HETATM" if hetatom else "ATOM",
                                     index,
                                     atom.name[0],
                                     atom.resname[0],
                                     atom.chain[0],
                                     resindex,
                                     ins if len(ins) else " ",
                                     atom.x[0],
                                     atom.y[0],
                                     atom.z[0],
                                     0.0, 0.0,
                                     atom.segname[0],
                                     atom.element[0])
        return result

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
