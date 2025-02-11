# Author: Robin Betz
#
# Copyright (C) 2015 Robin Betz
#
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
"""
This module contains functions for manipulating molecules using
the VMD python API.
"""

from __future__ import print_function
import os
import tempfile
import numpy as np
from vmd import molecule, atomsel

from dabble import DabbleError
from dabble.fileutils import concatenate_mae_files
# pylint: disable=no-member

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Constants
__1M_SALT_IONS_PER_WATER = 0.018

#==============================================================================

def get_net_charge(sel, molid):
    """
    Gets the net charge of an atom selection, using the charge
    field of the data.

    Args:
      sel (str): VMD atom selection to compute the charge of
      molid (int): VMD molecule id to select within

    Returns:
      (int): The rounded net charge of the selection

    Throws:
      ValueError: If charge does not round to an integer value
    """

    charge = np.array(atomsel(sel, molid=molid).charge)
    if charge.size == 0:
        return 0
    print("Calculating charge on %d atoms" % charge.size)

    # Check the system has charges defined
    if all(charge == 0):
        print("\nWARNING: All charges in selection are zero. "
              "Check the input file has formal charges defined!\n"
              "Selection was:\n%s\n"%sel)
        print(set(charge))

    # Round to nearest integer nd check this is okay
    net_charge = sum(charge)
    rslt = round(net_charge)
    if abs(rslt - net_charge) > 0.05:
        raise DabbleError("Total charge of %f is not integral within a "
                          "tolerance of 0.05. Check your input file."
                          % net_charge)

    return int(rslt)

#==========================================================================

def get_system_net_charge(molid):
    """
    Gets the net charge of the entire system.
    What is in the system is defined by the beta field, as atoms that won't
    be written have beta 0.

    Args:
      molid (int): VMD molecule id to compute the charge of

    Returns:
      (int): The net charge of the molecule
    """

    return get_net_charge(sel='beta 1', molid=molid)

#==========================================================================

def diameter(coords, chunkmem=30e6):
    """
    Returns the diameter of a set of xy coordinates.

    Args:
      coords (numpy array Nx2) : XY coordinates to get diameter of
      chunkmem (int) : Chunk memory for calculation

    Returns:
      (float, float): The diameter of the stuff in both dimensions
    """
    # pylint: disable=invalid-name
    coords = np.require(coords, dtype=np.float32)
    if coords.size == 0:
        return 0
    nper = int(chunkmem / (4*coords.size))
    D = np.array([np.inner(x, x) for x in coords])
    i = 0
    d = 0
    while i < len(coords):
        M = np.inner(-2*coords, coords[i:i+nper])
        M += D[i:i+nper]
        M += D[:, None]
        nd = M.max()
        if nd > d:
            d = nd
        i += nper
    return np.sqrt(d)

#==========================================================================

def solute_xy_diameter(solute_sel, molid):
    """
    Returns the XY diameter of a set of atoms.

    Args:
      solute_sel (str): VMD atom selection to get diameter of
      molid (int): VMD molecule ID to select within

    Returns:
      (float, float) X and Y diameter of the selection
    """

    sol = atomsel(solute_sel, molid=molid)
    return diameter(np.transpose([sol.x, sol.y]))

#==========================================================================

def get_num_salt_ions_needed(molid,
                             conc,
                             water_sel='water and element O',
                             cation='Na',
                             anion='Cl'):
    """
    Gets the number of salt ions needed to put the system at a given
    concentration of salt.

    Args:
      molid (int) : The VMD molecule ID to consider
      conc (float) : Desired salt concentration
      water_sel (str) : VMD atom selection for water
      cation (str) : Cation to use, either Na or K right now
      anion (str) : Anion to use, only Cl currently supported

    Returns:
      (float tuple) : # cations needed, # anions needed, number of waters
                      that will remain, total # cations, total # anions,
                      cation concentration, anion concentration

    Raises:
      Exception if number of cations and the net cation charge are
        not equal (should never happen)
    """
    # pylint: disable = too-many-branches, too-many-locals

    cations = atomsel_remaining(molid, 'element %s' % cation)
    anions = atomsel_remaining(molid, 'element %s' % anion)
    molid = molecule.get_top()
    try:
        abs(get_net_charge(str(cations), molid)-len(cations)) > 0.01
    except ValueError:
        # Check for bonded cations
        # Minimize the number of calls to atomsel
        nonbonded_cation_index = [cations.index[i] \
                                  for i in range(len(cations)) \
                                  if len(cations.bonds[i]) == 0]

        if not nonbonded_cation_index:
            cations = atomsel('none')
        else:
            cations = atomsel_remaining(molid,
                                        'index '+' '.join(nonbonded_cation_index))

        if abs(get_net_charge(str(cations), molid)-len(cations)) < 0.01:
            raise Exception('Num cations and net cation charge are not equal')
    try:
        abs(get_net_charge(str(anions), molid)+len(anions)) > 0.01
    except ValueError:
        # Check for bonded anions
        nonbonded_anion_index = [anions.index[i] \
                                 for i in range(len(anions)) \
                                 if len(anions.bonds[i]) == 0]
        if not nonbonded_anion_index:
            anions = atomsel('none')
        else:
            anions = atomsel_remaining(molid,
                                       'index '+' '.join(nonbonded_anion_index))
        if abs(get_net_charge(str(anions), molid)+len(anions)) < 0.01:
            raise Exception('num anions and abs anion charge are not equal')

    num_waters = num_atoms_remaining(molid, water_sel)
    num_for_conc = int(round(__1M_SALT_IONS_PER_WATER * num_waters * conc))
    pos_ions_needed = num_for_conc - len(cations)
    neg_ions_needed = num_for_conc - len(anions)
    system_charge = get_system_net_charge(molid)

    new_system_charge = system_charge + len(anions) - len(cations)
    to_neutralize = abs(new_system_charge)
    if new_system_charge > 0:
        if to_neutralize > pos_ions_needed:
            neg_ions_needed += to_neutralize - pos_ions_needed
            pos_ions_needed = 0
        else:
            pos_ions_needed -= to_neutralize
    else:
        if to_neutralize > neg_ions_needed:
            pos_ions_needed += to_neutralize - neg_ions_needed
            neg_ions_needed = 0
        neg_ions_needed -= to_neutralize

    # Check for less than 0
    pos_ions_needed = max(0, pos_ions_needed)
    neg_ions_needed = max(0, neg_ions_needed)

    total_cations = len(cations) + pos_ions_needed
    total_anions = len(anions) + neg_ions_needed

    # volume estimate from prev waters
    cation_conc = (float(total_cations) / num_waters) / __1M_SALT_IONS_PER_WATER
    anion_conc = (float(total_anions) / num_waters) / __1M_SALT_IONS_PER_WATER
    num_waters -= pos_ions_needed + neg_ions_needed

    return (pos_ions_needed,
            neg_ions_needed,
            num_waters,
            total_cations,
            total_anions,
            cation_conc,
            anion_conc)

#==========================================================================

def lipid_composition(lipid_sel, molid):
    """
    Calculates the lipid composition of each leaflet of the membrane

    Args:
      lipid_sel (str): VMD selection string for lipid
      molid (int) : VMD molecule ID to consider

    Returns:
      (int tuple) number of lipids on inner and outer membrane leaflets
    """

    def leaflet(leaflet_sel):
        """
        Returns the composition in one selected leaflet
        """
        selstr = "not element H C and (%s) and (%s)" % (lipid_sel, leaflet_sel)
        sel = atomsel_remaining(molid, selstr)
        resnames = set(sel.resname)

        dct = {s : len(set(atomsel_remaining(molid,
                                             "%s and resname '%s'"
                                             % (sel, s)).fragment))
               for s in resnames}
        return dct

    inner, outer = leaflet('z < 0'), leaflet('not (z < 0)')
    return inner, outer

#==========================================================================

def print_lipid_composition(lipid_sel, molid):
    """
    Describes the composition of the inner and outer leaflet

    Args:
       molid (int): VMD molecule id to look at
       lipid_sel (str): VMD atom selection for lipid

    Returns:
      (str) string describing the lipid composition
    """

    inner, outer = lipid_composition(lipid_sel, molid)
    desc = "Inner leaflet:"
    for kind, num in sorted(inner.items()):
        desc += "  %d %s\n" % (num, kind)
    desc += "Outer leaflet:"
    for kind, num in sorted(outer.items()):
        desc += "  %d %s\n" % (num, kind)

    return desc

#==========================================================================

def get_system_dimensions(molid):
    """
    Gets the periodic box dimensions of a system.

    Args:
      molid (int) : VMD molecule ID to consider

    Returns:
      (float tuple) : A, B, C box dimensions

    Raises:
      ValueError if no box is found
    """

    box = molecule.get_periodic(molid)

    if box['a'] == 0.0 and box['b'] == 0.0 and box['c'] == 0.0:
        raise Exception('No periodic box found in membrane!')
    return (box['a'], box['b'], box['c'])


#==========================================================================

def center_system(molid, tmp_dir, center_z=False):
    """
    Centers an entire system in the XY-plane, and optionally in the Z
    dimension. Needs to save and reload the file in case the current
    positions need to be concatenated to produce a new file.

    Args:
      molid (int): VMD molecule id to center
      tmp_dir (str): Directory to create temp file in
      center_z (bool): Whether or not to center along the Z axis as well

    Returns:
      (int) : VMD molecule id of centered system
    """
    # pylint: disable=invalid-name
    x, y, z = atomsel('all', molid=molid).center()

    if center_z is True:
        atomsel('all', molid=molid).moveby((-x, -y, -z))
    else:
        atomsel('all', molid=molid).moveby((-x, -y, 0))

    # Save and reload the solute to record atom positions
    temp_mae = tempfile.mkstemp(suffix='.mae',
                                prefix='dabble_centered',
                                dir=tmp_dir)[1]
    atomsel('all', molid=molid).write('mae', temp_mae)
    molecule.delete(molid)
    new_id = molecule.load('mae', temp_mae)
    return new_id

#==========================================================================

def set_ion(molid, atom_id, element):
    """
    Sets an atom to be the desired ion

    Args:
      molid (int): VMD molecule to operate on
      atom_id (int): Atom index to change to ion
      element (str in Na, K, Cl): Ion to apply

    Raises:
      ValueError if the index to change is not present
    """

    sel = atomsel('index %d' % atom_id, molid=molid)
    if not sel:
        raise ValueError("Index %d does not exist" % atom_id)

    resname = dict(Na='SOD', K='POT', Cl='CLA')[element]
    name = dict(Na='NA', K='K', Cl='CL')[element]
    attype = dict(Na='NA', K='K', Cl='CL')[element]
    charge = dict(Na=1, K=1, Cl=-1)[element]
    sel.element = element
    sel.name = name
    sel.type = attype
    sel.resname = resname
    sel.chain = 'N'
    sel.segid = 'ION'
    sel.charge = charge

#==========================================================================

def set_cations(molid, element, filter_sel='none'):
    """
    Sets all of the specified atoms to a cation

    Args:
      molid (int): VMD molecule ID to consider
      element (str in Na, K): Cation to convert
      filter_sel (str): VMD atom selection string for atoms to convert

    Raises:
      ValueError if invalid cation specified
    """

    if element not in ['Na', 'K']:
        raise DabbleError("Invalid cation '%s'. "
                          "Supported cations are Na, K" % element)

    for gid in tuple(atomsel('element K Na and not (%s)' % filter_sel)):
        set_ion(molid, gid, element)

#==========================================================================

def tile_system(input_id, times_x, times_y, times_z, tmp_dir):
    """
    Tiles the membrane or solvent system the given number of times
    in each direction to produce a larger system.

    Args:
      input_id (int): VMD molecule id to tile
      times_x (int): Number of times to tile in x direction
      times_y (int): Number of times to tile in y direction
      times_z (int): Number of times to tile in z direction
      tmp_dir (str): Directory in which to put temporary files

    Returns:
      (int) VMD molecule ID of tiled system
    """
    # pylint: disable=invalid-name, too-many-locals
    # Read in the equilibrated bilayer file
    new_resid = np.array(atomsel('all', molid=input_id).residue)
    num_residues = new_resid.max()
    atomsel('all', molid=input_id).user = 2.0
    wx, wy, wz = get_system_dimensions(molid=input_id)

    # Move the lipids over, save that file, move them back, repeat, then
    # stack all of those together to make a tiled membrane. Uses
    # temporary mae files to save each "tile" since this
    # format is easy to combine. Renumbers residues as it goes along.
    tile_filenames = []
    for nx in range(times_x):
        for ny in range(times_y):
            for nz in range(times_z):
                tx = np.array([nx * wx, ny * wy, nz * wz])
                atomsel('all', input_id).moveby(tuple(tx))
                atomsel('all', input_id).resid = [int(_) for _ in new_resid]
                new_resid += num_residues
                tile_filename = tempfile.mkstemp(suffix='.mae',
                                                 prefix='dabble_tile_tmp',
                                                 dir=tmp_dir)[1]
                tile_filenames.append(tile_filename)
                atomsel('all', molid=input_id).write('mae', tile_filename)
                atomsel('all', molid=input_id).moveby(tuple(-tx))

    # Write all of these tiles together into one large bilayer
    merge_output_filename = tempfile.mkstemp(suffix='.mae',
                                             prefix='dabble_merge_tile_tmp',
                                             dir=tmp_dir)[1]
    concatenate_mae_files(merge_output_filename,
                          input_filenames=tile_filenames)

    # Read that large bilayer file in as a new molecule and
    # write it as the output file
    output_id = molecule.load('mae', merge_output_filename)
    molecule.set_periodic(output_id, -1,
                          times_x * wx, times_y * wy, times_z * wz,
                          90.0, 90.0, 90.0)

    # Save and clean up
    atomsel('all', molid=output_id).write('mae', merge_output_filename)

    for tile_filename in tile_filenames:
        os.remove(tile_filename)
    return output_id

#==========================================================================

def combine_molecules(input_ids, tmp_dir):
    """
    Combines input molecules, closes them and returns the molecule id
    of the new molecule that combines them, putting it on top.

    Args:
      input_ids (list of int): Molecule IDs to combine, will be closed
      tmp_dir (str): Directory to put combined molecule into

    Returns:
      (int) molid of combined system
    """

    output_filename = tempfile.mkstemp(suffix='.mae',
                                       prefix='dabble_combine',
                                       dir=tmp_dir)[1]
    concatenate_mae_files(output_filename, input_ids=input_ids)
    output_id = molecule.load('mae', output_filename)
    molecule.set_top(output_id)
    for i in input_ids:
        molecule.delete(i)
    atomsel('all', molid=output_id).beta = 1
    return output_id

#==========================================================================

def atomsel_remaining(molid, sel):
    """
    Selects all remaining atoms. Whether or not an atom is counted
    is determined by value of the beta flag.

    Args:
      molid (int): VMD molecule id to consider
      sel (str): VMD atom selection string to grab, defaults to all

    Returns:
      VMD atomsel object representing the selection, or None
      if no atoms matched the selection
    """

    selection = atomsel('beta 1 and (%s)' % sel, molid)
    #if len(selection) == 0:
    #    return None
    #else:
    return selection

#==========================================================================

def num_atoms_remaining(molid, sel='all'):
    """
    Returns the number of atoms remaining in the system, indicated
    by the value of the beta flag.

    Args:
      molid (int): VMD molecule id to consider
      sel (str): VMD atom selection to count, defaults to all

    Returns:
      (int) number of atoms remaining in the system
    """

    return len(atomsel_remaining(molid, sel))

#==========================================================================

def num_waters_remaining(molid, water_sel='water and element O'):
    """
    Returns the number of waters remaining in the system, indicated
    by the value of the beta flag.

    Args:
      molid (int): VMD molecule id to consider
      sel (str): VMD atom selection that counts as water, defaults
        to 'water and element O'

    Returns:
      (int) number of water molecules remaining in the system

    Raises:
      ValueError if empty water selection
      ValueError if non-existent molecule given
    """
    if not water_sel:
        raise ValueError("Empty water selection string")
    if not molecule.exists(molid):
        raise ValueError("Invalid molecule %d" % molid)

    return len(atomsel_remaining(molid, water_sel))

#==========================================================================

def num_lipids_remaining(molid, lipid_sel):
    """
    Returns the number of lipids remaining in the system, indicated
    by the value of the beta flag. Uses the fragment notation to count
    the number of lipids.

    Args:
      molid (int): VMD molecule ID to consider
      lipid_sel (str): VMD atom selection that counts as lipid

    Returns:
      (int) number of lipid molecules remaining in the system

    Raises:
      ValueError if empty lipid selection
      ValueError if non-existent molecule given
    """

    if not lipid_sel:
        raise ValueError("Empty lipid selection string")
    if not molecule.exists(molid):
        raise ValueError("Invalid molecule %d" % molid)

    return np.unique(atomsel_remaining(molid, lipid_sel).fragment).size

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
