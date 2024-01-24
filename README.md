## Dabble-Mod ##
Dabble modified to allow addition of both Na+ and K+ at once.

Installation intially is still the same:

```
conda config --add channels omnia # otherwise can’t install parmed
conda config --add channels defaults # Don’t want omnia to be the highest priority channel...
conda config --add channels conda-forge
conda install -c rbetz dabble
```

But follow this up with

`pip install -e .`

in the git directory

An important bug to consider: for het atoms/ligands, even if the molecules have different chain letters, having the same residue number will lead to all but one being deleted during the dabble run. If there are lipids in the system, ensure they have different chain letters AND residue numbers.

## Dabble ##
[![GPLv2](https://img.shields.io/github/license/drorlab/dabble.svg)](http://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)
[![DOI](https://zenodo.org/badge/29268375.svg)](https://zenodo.org/badge/latestdoi/29268375)
![Downloads](https://anaconda.org/rbetz/dabble/badges/downloads.svg)
![CI status](https://img.shields.io/travis/Eigenstate/dabble.svg)

Dabble makes molecular dynamics system building easy!

No more messing with atom names or lipid membranes, Dabble does all the work for you.
Supports multiple forcefields (CHARMM and AMBER), and simulation packages! Currently,
that's CHARMM, AMBER, Desmond, and Anton!

[<img src="http://dabble.robinbetz.com/_images/dabblebox.png" width="300px">](http://dabble.robinbetz.com)

# <center> [Read the Documentation!](http://dabble.robinbetz.com) </center>

