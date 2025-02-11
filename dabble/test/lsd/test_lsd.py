# Tests multiple ligands
import os
from vmd import atomsel, molecule

dir = os.path.dirname(__file__) + "/"
#==============================================================================

def test_amber_params(tmpdir):
    """
    Tests writing a ligand with amber parameters
    """
    from dabble.param import AmberWriter

    # Parameterize with amber parameters
    p = str(tmpdir)
    molid = molecule.load("mae", os.path.join(dir, "07HT2B_WT.mae"))
    w = AmberWriter(molid, tmp_dir=p, forcefield="amber", hmr=False,
                    extra_topos=[os.path.join(dir,"lsd.lib")],
                    extra_params=[os.path.join(dir, "lsd.frcmod")],
                    override_defaults=False)
    w.write(os.path.join(p, "test"))

    # Check output is correct
    m2 = molecule.load("parm7", os.path.join(p, "test.prmtop"),
                       "rst7", os.path.join(p, "test.inpcrd"))
    molecule.set_top(m2)

    # Check the system is correctly built
    assert len(set(atomsel("protein or resname ACE NMA").resid)) == 298
    assert len(atomsel("water")) == 186
    assert len(atomsel("ion")) == 0

    # Check the LSD and CHL (cholesterol) are present
    assert len(atomsel("resname LSD")) == 50
    assert len(atomsel("resname CHL")) == 74

    # Check the partial charges are set
    # Here the LSD library has partial charges of 0 except +0.6 on the N2
    assert len(set(atomsel("resname LSD").charge)) == 2
    assert abs(atomsel("resname LSD and name N2").charge[0] - 0.6) < 0.01
    assert abs(set(atomsel("resname LSD and not name N2").charge).pop()) < 0.01

#==============================================================================
