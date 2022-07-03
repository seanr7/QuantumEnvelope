#!/usr/bin/env python3

# Types
# -----
from typing import Tuple, Dict, NewType, NamedTuple, List, Set, Iterator, NewType
from dataclasses import dataclass

# Yes, I like itertools
from itertools import chain, product, combinations, takewhile, permutations
from functools import partial, cached_property, cache
from collections import defaultdict
import numpy as np
from math import sqrt
import random


# Orbital index (0,1,2,...,n_orb-1)
OrbitalIdx = NewType("OrbitalIdx", int)
# Two-electron integral :
# $<ij|kl> = \int \int \phi_i(r_1) \phi_j(r_2) \frac{1}{|r_1 - r_2|} \phi_k(r_1) \phi_l(r_2) dr_1 dr_2$
Two_electron_integral_index = Tuple[OrbitalIdx, OrbitalIdx, OrbitalIdx, OrbitalIdx]
Two_electron_integral = Dict[Two_electron_integral_index, float]

Two_electron_integral_index_phase = Tuple[Two_electron_integral_index, bool]

# One-electron integral :
# $<i|h|k> = \int \phi_i(r) (-\frac{1}{2} \Delta + V_en ) \phi_k(r) dr$
One_electron_integral = Dict[Tuple[OrbitalIdx, OrbitalIdx], float]
Spin_determinant = Tuple[OrbitalIdx, ...]


class Determinant(NamedTuple):
    """Slater determinant: Product of 2 determinants.
    One for $\alpha$ electrons and one for \beta electrons."""

    alpha: Spin_determinant
    beta: Spin_determinant


Psi_det = List[Determinant]
Psi_coef = List[float]
# We have two type of energy.
# The varitional Energy who correpond Psi_det
# The pt2 Energy who correnpond to the pertubative energy induce by each determinant connected to Psi_det
Energy = NewType("Energy", float)

# _____          _           _               _   _ _   _ _
# |_   _|        | |         (_)             | | | | | (_) |
#  | | _ __   __| | _____  ___ _ __   __ _  | | | | |_ _| |___
#  | || '_ \ / _` |/ _ \ \/ / | '_ \ / _` | | | | | __| | / __|
# _| || | | | (_| |  __/>  <| | | | | (_| | | |_| | |_| | \__ \
# \___/_| |_|\__,_|\___/_/\_\_|_| |_|\__, |  \___/ \__|_|_|___/
#                                     __/ |
#                                    |___/


@cache
def compound_idx2(i, j):
    """
    get compound (triangular) index from (i,j)

    (first few elements of lower triangle shown below)
          j
        │ 0   1   2   3
     ───┼───────────────
    i 0 │ 0
      1 │ 1   2
      2 │ 3   4   5
      3 │ 6   7   8   9

    position of i,j in flattened triangle

    >>> compound_idx2(0,0)
    0
    >>> compound_idx2(0,1)
    1
    >>> compound_idx2(1,0)
    1
    >>> compound_idx2(1,1)
    2
    >>> compound_idx2(1,2)
    4
    >>> compound_idx2(2,1)
    4
    """
    p, q = min(i, j), max(i, j)
    return (q * (q + 1)) // 2 + p


@cache
def compound_idx4(i, j, k, l):
    """
    nested calls to compound_idx2
    >>> compound_idx4(0,0,0,0)
    0
    >>> compound_idx4(0,1,0,0)
    1
    >>> compound_idx4(1,1,0,0)
    2
    >>> compound_idx4(1,0,1,0)
    3
    >>> compound_idx4(1,0,1,1)
    4
    """
    return compound_idx2(compound_idx2(i, k), compound_idx2(j, l))


@cache
def compound_idx2_reverse(ij):
    """
    inverse of compound_idx2
    returns (i, j) with i <= j
    >>> compound_idx2_reverse(0)
    (0, 0)
    >>> compound_idx2_reverse(1)
    (0, 1)
    >>> compound_idx2_reverse(2)
    (1, 1)
    >>> compound_idx2_reverse(3)
    (0, 2)
    """
    j = int((sqrt(1 + 8 * ij) - 1) / 2)
    i = ij - (j * (j + 1) // 2)
    return i, j


def compound_idx4_reverse(ijkl):
    """
    inverse of compound_idx4
    returns (i, j, k, l) with ik <= jl, i <= k, and j <= l (i.e. canonical ordering)
    where ik == compound_idx2(i, k) and jl == compound_idx2(j, l)
    >>> compound_idx4_reverse(0)
    (0, 0, 0, 0)
    >>> compound_idx4_reverse(1)
    (0, 0, 0, 1)
    >>> compound_idx4_reverse(2)
    (0, 0, 1, 1)
    >>> compound_idx4_reverse(3)
    (0, 1, 0, 1)
    >>> compound_idx4_reverse(37)
    (0, 2, 1, 3)
    """
    ik, jl = compound_idx2_reverse(ijkl)
    i, k = compound_idx2_reverse(ik)
    j, l = compound_idx2_reverse(jl)
    return i, j, k, l


@cache
def compound_idx4_reverse_all(ijkl):
    """
    return all 8 permutations that are equivalent for real orbitals
    returns 8 4-tuples, even when there are duplicates
    for complex orbitals, they are ordered as:
    v, v, v*, v*, u, u, u*, u*
    where v == <ij|kl>, u == <ij|lk>, and * denotes the complex conjugate
    >>> compound_idx4_reverse_all(0)
    ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    >>> compound_idx4_reverse_all(1)
    ((0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0))
    >>> compound_idx4_reverse_all(37)
    ((0, 2, 1, 3), (2, 0, 3, 1), (1, 3, 0, 2), (3, 1, 2, 0), (0, 3, 1, 2), (3, 0, 2, 1), (1, 2, 0, 3), (2, 1, 3, 0))
    """
    i, j, k, l = compound_idx4_reverse(ijkl)
    return (
        (i, j, k, l),
        (j, i, l, k),
        (k, l, i, j),
        (l, k, j, i),
        (i, l, k, j),
        (l, i, j, k),
        (k, j, i, l),
        (j, k, l, i),
    )


@cache
def compound_idx4_reverse_all_unique(ijkl):
    """
    return only the unique 4-tuples from compound_idx4_reverse_all
    """
    return tuple(set(compound_idx4_reverse_all(ijkl)))


def canonical_idx4(i, j, k, l):
    """
    for real orbitals, return same 4-tuple for all equivalent integrals
    returned (i,j,k,l) should satisfy the following:
        i <= k
        j <= l
        (k < l) or (k==l and i <= j)
    the last of these is equivalent to (compound_idx2(i,k) <= compound_idx2(j,l))
    >>> canonical_idx4(1, 0, 0, 0)
    (0, 0, 0, 1)
    >>> canonical_idx4(4, 2, 3, 1)
    (1, 3, 2, 4)
    >>> canonical_idx4(3, 2, 1, 4)
    (1, 2, 3, 4)
    >>> canonical_idx4(1, 3, 4, 2)
    (2, 1, 3, 4)
    """
    i, k = min(i, k), max(i, k)
    ik = compound_idx2(i, k)
    j, l = min(j, l), max(j, l)
    jl = compound_idx2(j, l)
    if ik <= jl:
        return i, j, k, l
    else:
        return j, i, l, k


#  _____      _                       _   _
# |_   _|    | |                     | | | |
#   | | _ __ | |_ ___  __ _ _ __ __ _| | | |_ _   _ _ __   ___  ___
#   | || '_ \| __/ _ \/ _` | '__/ _` | | | __| | | | '_ \ / _ \/ __|
#  _| || | | | ||  __/ (_| | | | (_| | | | |_| |_| | |_) |  __/\__ \
#  \___/_| |_|\__\___|\__, |_|  \__,_|_|  \__|\__, | .__/ \___||___/
#                      __/ |                   __/ | |
#                     |___/                   |___/|_|


def integral_category(i, j, k, l):
    """
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    | label |                   | ik/jl i/k j/l | i/j j/k k/l i/l | singles                       | doubles                      | diagonal                    |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |   A   | i=j=k=l (1,1,1,1) |   =    =   =  |  =   =   =   =  |                               |                              | coul. (1 occ. both spins?)  |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |   B   | i=k<j=l (1,2,1,2) |   <    =   =  |  <   >   <   <  |                               |                              | coul. (1,2 any spin occ.?)  |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |       | i=k<j<l (1,2,1,3) |   <    =   <  |  <   >   <   <  | 2<->3, 1 occ. (any spin)      |                              |                             |
    |   C   | i<k<j=l (1,3,2,3) |   <    <   =  |  <   >   <   <  | 1<->2, 3 occ. (any spin)      |                              |                             |
    |       | j<i=k<l (2,1,2,3) |   <    =   <  |  >   <   <   <  | 1<->3, 2 occ. (any spin)      |                              |                             |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |   D   | i=j=k<l (1,1,1,2) |   <    =   <  |  =   =   <   <  | 1<->2, 1 occ. (opposite spin) |                              |                             |
    |       | i<j=k=l (1,2,2,2) |   <    <   =  |  <   =   =   <  | 1<->2, 2 occ. (opposite spin) |                              |                             |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |       | i=j<k<l (1,1,2,3) |   <    <   <  |  =   <   <   <  | 2<->3, 1 occ. (same spin)     | 1a<->2a x 1b<->3b, (and a/b) |                             |
    |   E   | i<j=k<l (1,2,2,3) |   <    <   <  |  <   =   <   <  | 1<->3, 2 occ. (same spin)     | 1a<->2a x 2b<->3b, (and a/b) |                             |
    |       | i<j<k=l (1,2,3,3) |   <    <   <  |  <   <   =   <  | 1<->2, 3 occ. (same spin)     | 1a<->3a x 2b<->3b, (and a/b) |                             |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |   F   | i=j<k=l (1,1,2,2) |   =    <   <  |  =   <   =   <  |                               | 1a<->2a x 1b<->2b            | exch. (1,2 same spin occ.?) |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    |       | i<j<k<l (1,2,3,4) |   <    <   <  |  <   <   <   <  |                               | 1<->3 x 2<->4                |                             |
    |   G   | i<k<j<l (1,3,2,4) |   <    <   <  |  <   >   <   <  |                               | 1<->2 x 3<->4                |                             |
    |       | j<i<k<l (2,1,3,4) |   <    <   <  |  >   <   <   <  |                               | 1<->4 x 2<->3                |                             |
    +-------+-------------------+---------------+-----------------+-------------------------------+------------------------------+-----------------------------+
    """
    assert (i, j, k, l) == canonical_idx4(i, j, k, l)
    if i == l:
        return "A"
    elif (i == k) and (j == l):
        return "B"
    elif (i == k) or (j == l):
        if j == k:
            return "D"
        else:
            return "C"
    elif j == k:
        return "E"
    elif (i == j) and (k == l):
        return "F"
    elif (i == j) or (k == l):
        return "E"
    else:
        return "G"


#   _____      _ _   _       _ _          _   _
#  |_   _|    (_) | (_)     | (_)        | | (_)
#    | | _ __  _| |_ _  __ _| |_ ______ _| |_ _  ___  _ __
#    | || '_ \| | __| |/ _` | | |_  / _` | __| |/ _ \| '_ \
#   _| || | | | | |_| | (_| | | |/ / (_| | |_| | (_) | | | |
#   \___/_| |_|_|\__|_|\__,_|_|_/___\__,_|\__|_|\___/|_| |_|

# ~
# Integrals of the Hamiltonian over molecular orbitals
# ~
def load_integrals(
    fcidump_path,
) -> Tuple[int, float, One_electron_integral, Two_electron_integral]:
    """Read all the Hamiltonian integrals from the data file.
    Returns: (E0, d_one_e_integral, d_two_e_integral).
    E0 : a float containing the nuclear repulsion energy (V_nn),
    d_one_e_integral : a dictionary of one-electron integrals,
    d_two_e_integral : a dictionary of two-electron integrals.
    """
    import glob

    if len(glob.glob(fcidump_path)) == 1:
        fcidump_path = glob.glob(fcidump_path)[0]
    elif len(glob.glob(fcidump_path)) == 0:
        print("no matching fcidump file")
    else:
        print(f"multiple matches for {fcidump_path}")
        for i in glob.glob(fcidump_path):
            print(i)

    # Use an iterator to avoid storing everything in memory twice.
    if fcidump_path.split(".")[-1] == "gz":
        import gzip

        f = gzip.open(fcidump_path)
    elif fcidump_path.split(".")[-1] == "bz2":
        import bz2

        f = bz2.open(fcidump_path)
    else:
        f = open(fcidump_path)

    # Only non-zero integrals are stored in the fci_dump.
    # Hence we use a defaultdict to handle the sparsity
    n_orb = int(next(f).split()[2])

    for _ in range(3):
        next(f)

    d_one_e_integral = defaultdict(int)
    d_two_e_integral = defaultdict(int)

    for line in f:
        v, *l = line.split()
        v = float(v)
        # Transform from Mulliken (ik|jl) to Dirac's <ij|kl> notation
        # (swap indices)
        i, k, j, l = list(map(int, l))

        if i == 0:
            E0 = v
        elif j == 0:
            # One-electron integrals are symmetric (when real, not complex)
            d_one_e_integral[
                (i - 1, k - 1)
            ] = v  # index minus one to be consistent with determinant orbital indexing starting at zero
            d_one_e_integral[(k - 1, i - 1)] = v
        else:
            # Two-electron integrals have many permutation symmetries:
            # Exchange r1 and r2 (indices i,k and j,l)
            # Exchange i,k
            # Exchange j,l
            key = compound_idx4(i - 1, j - 1, k - 1, l - 1)
            d_two_e_integral[key] = v

    f.close()

    return n_orb, E0, d_one_e_integral, d_two_e_integral


def load_wf(path_wf) -> Tuple[List[float], List[Determinant]]:
    """Read the input file :
    Representation of the Slater determinants (basis) and
    vector of coefficients in this basis (wave function)."""

    import glob

    if len(glob.glob(path_wf)) == 1:
        path_wf = glob.glob(path_wf)[0]
    elif len(glob.glob(path_wf)) == 0:
        print(f"no matching wf file: {path_wf}")
    else:
        print(f"multiple matches for {path_wf}")
        for i in glob.glob(path_wf):
            print(i)

    if path_wf.split(".")[-1] == "gz":
        import gzip

        with gzip.open(path_wf) as f:
            data = f.read().decode().split()
    elif path_wf.split(".")[-1] == "bz2":
        import bz2

        with bz2.open(path_wf) as f:
            data = f.read().decode().split()
    else:
        with open(path_wf) as f:
            data = f.read().split()

    def decode_det(str_):
        for i, v in enumerate(str_):
            if v == "+":
                yield i

    def grouper(iterable, n):
        "Collect data into fixed-length chunks or blocks"
        args = [iter(iterable)] * n
        return zip(*args)

    det = []
    psi_coef = []
    for (coef, det_i, det_j) in grouper(data, 3):
        psi_coef.append(float(coef))
        det.append(Determinant(tuple(decode_det(det_i)), tuple(decode_det(det_j))))

    # Normalize psi_coef

    norm = sqrt(sum(c * c for c in psi_coef))
    psi_coef = [c / norm for c in psi_coef]

    return psi_coef, det


def load_eref(path_ref) -> Energy:
    """Read the input file :
    Representation of the Slater determinants (basis) and
    vector of coefficients in this basis (wave function)."""

    import glob

    if len(glob.glob(path_ref)) == 1:
        path_ref = glob.glob(path_ref)[0]
    elif len(glob.glob(path_ref)) == 0:
        print(f"no matching ref file: {path_ref}")
    else:
        print(f"multiple matches for {path_ref}")
        for i in glob.glob(path_ref):
            print(i)

    if path_ref.split(".")[-1] == "gz":
        import gzip

        with gzip.open(path_ref) as f:
            data = f.read().decode()
    elif path_ref.split(".")[-1] == "bz2":
        import bz2

        with bz2.open(path_ref) as f:
            data = f.read().decode()
    else:
        with open(path_ref) as f:
            data = f.read()

    import re

    return float(re.search(r"E +=.+", data).group(0).strip().split()[-1])


#   _____         _ _        _   _
#  |  ___|       (_) |      | | (_)
#  | |____  _____ _| |_ __ _| |_ _  ___  _ __
#  |  __\ \/ / __| | __/ _` | __| |/ _ \| '_ \
#  | |___>  < (__| | || (_| | |_| | (_) | | | |
#  \____/_/\_\___|_|\__\__,_|\__|_|\___/|_| |_|
#
class Excitation:
    def __init__(self, n_orb):
        self.all_orbs = frozenset(range(n_orb))

    def gen_all_excitation(self, spindet: Spin_determinant, ed: int) -> Iterator:
        """
        Generate list of pair -> hole from a determinant spin.

        >>> sorted(Excitation(4).gen_all_excitation((0, 1),2))
        [((0, 1), (2, 3))]
        >>> sorted(Excitation(4).gen_all_excitation((0, 1),1))
        [((0,), (2,)), ((0,), (3,)), ((1,), (2,)), ((1,), (3,))]
        """
        holes = combinations(spindet, ed)
        not_spindet = self.all_orbs - set(spindet)
        parts = combinations(not_spindet, ed)
        return product(holes, parts)

    @staticmethod
    def apply_excitation(spindet, exc: Tuple[Tuple[int, ...], Tuple[int, ...]]):
        lh, lp = exc
        s = (set(spindet) - set(lh)) | set(lp)
        return tuple(sorted(s))

    def gen_all_connected_spindet(self, spindet: Spin_determinant, ed: int) -> Iterator:
        """
        Generate all the posible spin determinant relative to a excitation degree

        >>> sorted(Excitation(4).gen_all_connected_spindet((0, 1), 1))
        [(0, 2), (0, 3), (1, 2), (1, 3)]
        """
        l_exc = self.gen_all_excitation(spindet, ed)
        apply_excitation_to_spindet = partial(Excitation.apply_excitation, spindet)
        return map(apply_excitation_to_spindet, l_exc)

    def gen_all_connected_det_from_det(self, det: Determinant) -> Iterator[Determinant]:
        """
        Generate all the determinant who are single or double exictation (aka connected) from the input determinant

        >>> sorted(Excitation(3).gen_all_connected_det_from_det( Determinant((0, 1), (0,))))
        [Determinant(alpha=(0, 1), beta=(1,)),
         Determinant(alpha=(0, 1), beta=(2,)),
         Determinant(alpha=(0, 2), beta=(0,)),
         Determinant(alpha=(0, 2), beta=(1,)),
         Determinant(alpha=(0, 2), beta=(2,)),
         Determinant(alpha=(1, 2), beta=(0,)),
         Determinant(alpha=(1, 2), beta=(1,)),
         Determinant(alpha=(1, 2), beta=(2,))]
        """

        # All single exitation from alpha or for beta determinant
        # Then the production of the alpha, and beta (its a double)
        # Then the double exitation form alpha or beta

        # We use l_single_a, and l_single_b twice. So we store them.
        l_single_a = set(self.gen_all_connected_spindet(det.alpha, 1))
        l_double_aa = self.gen_all_connected_spindet(det.alpha, 2)

        s_a = (Determinant(det_alpha, det.beta) for det_alpha in chain(l_single_a, l_double_aa))

        l_single_b = set(self.gen_all_connected_spindet(det.beta, 1))
        l_double_bb = self.gen_all_connected_spindet(det.beta, 2)

        s_b = (Determinant(det.alpha, det_beta) for det_beta in chain(l_single_b, l_double_bb))

        l_double_ab = product(l_single_a, l_single_b)

        s_ab = (Determinant(det_alpha, det_beta) for det_alpha, det_beta in l_double_ab)

        return chain(s_a, s_b, s_ab)

    def gen_all_connected_determinant(self, psi_det: Psi_det) -> Psi_det:
        """
        >>> d1 = Determinant((0, 1), (0,) ) ; d2 = Determinant((0, 2), (0,) )
        >>> len(Excitation(4).gen_all_connected_determinant( [ d1,d2 ] ))
        22

        We remove the connected determinant who are already inside the wave function. Order doesn't matter
        """
        return list(
            set(chain.from_iterable(map(self.gen_all_connected_det_from_det, psi_det)))
            - set(psi_det)
        )

    @staticmethod
    @cache
    def exc_degree_spindet(spindet_i: Spin_determinant, spindet_j: Spin_determinant) -> int:
        return len(set(spindet_i).symmetric_difference(set(spindet_j))) // 2

    @staticmethod
    # @cache
    def exc_degree(det_i: Determinant, det_j: Determinant) -> Tuple[int, int]:
        """Compute the excitation degree, the number of orbitals which differ
           between the two determinants.
        >>> Excitation.exc_degree(Determinant(alpha=(0, 1), beta=(0, 1)),
        ...                     Determinant(alpha=(0, 2), beta=(4, 6)))
        (1, 2)
        """
        ed_up = Excitation.exc_degree_spindet(det_i.alpha, det_j.alpha)
        ed_dn = Excitation.exc_degree_spindet(det_i.beta, det_j.beta)
        return (ed_up, ed_dn)


#  ______ _                        _   _       _
#  | ___ \ |                      | | | |     | |
#  | |_/ / |__   __ _ ___  ___    | |_| | ___ | | ___
#  |  __/| '_ \ / _` / __|/ _ \   |  _  |/ _ \| |/ _ \
#  | |   | | | | (_| \__ \  __/_  | | | | (_) | |  __/
#  \_|   |_| |_|\__,_|___/\___( ) \_| |_/\___/|_|\___|
#                             |/
#
#                   _  ______          _   _      _
#                  | | | ___ \        | | (_)    | |
#    __ _ _ __   __| | | |_/ /_ _ _ __| |_ _  ___| | ___  ___
#   / _` | '_ \ / _` | |  __/ _` | '__| __| |/ __| |/ _ \/ __|
#  | (_| | | | | (_| | | | | (_| | |  | |_| | (__| |  __/\__ \
#   \__,_|_| |_|\__,_| \_|  \__,_|_|   \__|_|\___|_|\___||___/
#
#
class PhaseIdx(object):
    @staticmethod
    def single_phase(sdet_i, sdet_j, h, p):
        phase = 1
        for det, idx in ((sdet_i, h), (sdet_j, p)):
            for _ in takewhile(lambda x: x != idx, det):
                phase = -phase
        return phase

    @staticmethod
    def single_exc_no_phase(
        sdet_i: Spin_determinant, sdet_j: Spin_determinant
    ) -> Tuple[OrbitalIdx, OrbitalIdx]:
        """hole, particle of <I|H|J> when I and J differ by exactly one orbital
           h is occupied only in I
           p is occupied only in J

        >>> PhaseIdx.single_exc_no_phase((1, 5, 7), (1, 23, 7))
        (5, 23)
        >>> PhaseIdx.single_exc_no_phase((1, 2, 9), (1, 9, 18))
        (2, 18)
        """
        (h,) = set(sdet_i) - set(sdet_j)
        (p,) = set(sdet_j) - set(sdet_i)

        return h, p

    @staticmethod
    def single_exc(
        sdet_i: Spin_determinant, sdet_j: Spin_determinant
    ) -> Tuple[int, OrbitalIdx, OrbitalIdx]:
        """phase, hole, particle of <I|H|J> when I and J differ by exactly one orbital
           h is occupied only in I
           p is occupied only in J

        >>> PhaseIdx.single_exc((0, 4, 6), (0, 22, 6))
        (1, 4, 22)
        >>> PhaseIdx.single_exc((0, 1, 8), (0, 8, 17))
        (-1, 1, 17)
        """
        h, p = PhaseIdx.single_exc_no_phase(sdet_i, sdet_j)

        return PhaseIdx.single_phase(sdet_i, sdet_j, h, p), h, p

    @staticmethod
    def double_phase(sdet_i, sdet_j, h1, h2, p1, p2):
        # Compute phase. See paper to have a loopless algorithm
        # https://arxiv.org/abs/1311.6244
        phase = PhaseIdx.single_phase(sdet_i, sdet_j, h1, p1) * PhaseIdx.single_phase(
            sdet_j, sdet_i, p2, h2
        )
        if h2 < h1:
            phase *= -1
        if p2 < p1:
            phase *= -1
        return phase

    @staticmethod
    def double_exc_no_phase(
        sdet_i: Spin_determinant, sdet_j: Spin_determinant
    ) -> Tuple[OrbitalIdx, OrbitalIdx, OrbitalIdx, OrbitalIdx]:
        """holes, particles of <I|H|J> when I and J differ by exactly two orbitals
           h1, h2 are occupied only in I
           p1, p2 are occupied only in J

        >>> PhaseIdx.double_exc_no_phase((1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 5, 6, 7, 8, 9, 12, 13))
        (3, 4, 12, 13)
        >>> PhaseIdx.double_exc_no_phase((1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 4, 5, 6, 7, 8, 12, 18))
        (3, 9, 12, 18)
        """

        # Holes
        h1, h2 = sorted(set(sdet_i) - set(sdet_j))

        # Particles
        p1, p2 = sorted(set(sdet_j) - set(sdet_i))

        return h1, h2, p1, p2

    @staticmethod
    def double_exc(
        sdet_i: Spin_determinant, sdet_j: Spin_determinant
    ) -> Tuple[int, OrbitalIdx, OrbitalIdx, OrbitalIdx, OrbitalIdx]:
        """phase, holes, particles of <I|H|J> when I and J differ by exactly two orbitals
           h1, h2 are occupied only in I
           p1, p2 are occupied only in J

        >>> PhaseIdx.double_exc((0, 1, 2, 3, 4, 5, 6, 7, 8), (0, 1, 4, 5, 6, 7, 8, 11, 12))
        (1, 2, 3, 11, 12)
        >>> PhaseIdx.double_exc((0, 1, 2, 3, 4, 5, 6, 7, 8), (0, 1, 3, 4, 5, 6, 7, 11, 17))
        (-1, 2, 8, 11, 17)
        """

        h1, h2, p1, p2 = PhaseIdx.double_exc_no_phase(sdet_i, sdet_j)

        return PhaseIdx.double_phase(sdet_i, sdet_j, h1, h2, p1, p2), h1, h2, p1, p2


#   _   _                 _ _ _              _
#  | | | |               (_) | |            (_)
#  | |_| | __ _ _ __ ___  _| | |_ ___  _ __  _  __ _ _ __
#  |  _  |/ _` | '_ ` _ \| | | __/ _ \| '_ \| |/ _` | '_ \
#  | | | | (_| | | | | | | | | || (_) | | | | | (_| | | | |
#  \_| |_/\__,_|_| |_| |_|_|_|\__\___/|_| |_|_|\__,_|_| |_|
#

#    _             _
#   / \ ._   _    |_ |  _   _ _|_ ._ _  ._
#   \_/ | | (/_   |_ | (/_ (_  |_ | (_) | |
#
@dataclass
class Hamiltonian_one_electron(object):
    """
    One-electron part of the Hamiltonian: Kinetic energy (T) and
    Nucleus-electron potential (V_{en}). This matrix is symmetric.
    """

    integrals: One_electron_integral
    E0: Energy

    def H_ij_orbital(self, i: OrbitalIdx, j: OrbitalIdx) -> float:

        return self.integrals[(i, j)]

    def H_ii(self, det_i: Determinant) -> Energy:
        """Diagonal element of the Hamiltonian : <I|H|I>."""
        res = self.E0
        res += sum(self.H_ij_orbital(i, i) for i in det_i.alpha)
        res += sum(self.H_ij_orbital(i, i) for i in det_i.beta)
        return res

    def H_ij(self, det_i: Determinant, det_j: Determinant) -> Energy:
        """General function to dispatch the evaluation of H_ij"""

        def H_ij_spindet(sdet_i: Spin_determinant, sdet_j: Spin_determinant) -> Energy:
            """<I|H|J>, when I and J differ by exactly one orbital."""
            phase, m, p = PhaseIdx.single_exc(sdet_i, sdet_j)
            return self.H_ij_orbital(m, p) * phase

        ed_up, ed_dn = Excitation.exc_degree(det_i, det_j)
        # Same determinant -> Diagonal element
        if (ed_up, ed_dn) == (0, 0):
            return self.H_ii(det_i)
        # Single excitation
        elif (ed_up, ed_dn) == (1, 0):
            return H_ij_spindet(det_i.alpha, det_j.alpha)
        elif (ed_up, ed_dn) == (0, 1):
            return H_ij_spindet(det_i.beta, det_j.beta)
        else:
            return 0.0

    def H(self, psi_i, psi_j) -> List[List[Energy]]:
        h = np.array([self.H_ij(det_i, det_j) for det_i, det_j in product(psi_i, psi_j)])
        return h.reshape(len(psi_i), len(psi_j))


#   ___            _
#    |       _    |_ |  _   _ _|_ ._ _  ._   _
#    | \/\/ (_)   |_ | (/_ (_  |_ | (_) | | _>
#    _                                          _
#   | \  _ _|_  _  ._ ._ _  o ._   _. ._ _|_   | \ ._ o     _  ._
#   |_/ (/_ |_ (/_ |  | | | | | | (_| | | |_   |_/ |  | \/ (/_ | |
#
@dataclass
class Hamiltonian_two_electrons_determinant_driven(object):
    d_two_e_integral: Two_electron_integral

    def H_ijkl_orbital(self, i: OrbitalIdx, j: OrbitalIdx, k: OrbitalIdx, l: OrbitalIdx) -> float:
        """Assume that *all* the integrals are in
        `d_two_e_integral` In this function, for simplicity we don't use any
        symmetry sparse representation.  For real calculations, symmetries and
        storing only non-zeros needs to be implemented to avoid an explosion of
        the memory requirements."""
        key = compound_idx4(i, j, k, l)
        return self.d_two_e_integral[key]

    @staticmethod
    def H_ii_indices(det_i: Determinant) -> Iterator[Two_electron_integral_index_phase]:
        """Diagonal element of the Hamiltonian : <I|H|I>.
        >>> sorted(Hamiltonian_two_electrons_determinant_driven.H_ii_indices( Determinant((0,1),(2,3))))
        [((0, 1, 0, 1), 1), ((0, 1, 1, 0), -1), ((0, 2, 0, 2), 1), ((0, 3, 0, 3), 1),
         ((1, 2, 1, 2), 1), ((1, 3, 1, 3), 1), ((2, 3, 2, 3), 1), ((2, 3, 3, 2), -1)]
        """
        for i, j in combinations(det_i.alpha, 2):
            yield (i, j, i, j), 1
            yield (i, j, j, i), -1

        for i, j in combinations(det_i.beta, 2):
            yield (i, j, i, j), 1
            yield (i, j, j, i), -1

        for i, j in product(det_i.alpha, det_i.beta):
            yield (i, j, i, j), 1

    @staticmethod
    def H_ij_indices(
        det_i: Determinant, det_j: Determinant
    ) -> Iterator[Two_electron_integral_index_phase]:
        """General function to dispatch the evaluation of H_ij"""

        def H_ij_single_indices(
            sdet_i: Spin_determinant, sdet_j: Spin_determinant, sdet_k: Spin_determinant
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly one orbital"""
            phase, h, p = PhaseIdx.single_exc(sdet_i, sdet_j)
            for i in sdet_i:
                yield (h, i, p, i), phase
                yield (h, i, i, p), -phase
            for i in sdet_k:
                yield (h, i, p, i), phase

        def H_ij_doubleAA_indices(
            sdet_i: Spin_determinant, sdet_j: Spin_determinant
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly two orbitals within
            the same spin."""
            phase, h1, h2, p1, p2 = PhaseIdx.double_exc(sdet_i, sdet_j)
            yield (h1, h2, p1, p2), phase
            yield (h1, h2, p2, p1), -phase

        def H_ij_doubleAB_2e_index(
            det_i: Determinant, det_j: Determinant
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly one alpha spin-orbital and
            one beta spin-orbital."""
            phaseA, h1, p1 = PhaseIdx.single_exc(det_i.alpha, det_j.alpha)
            phaseB, h2, p2 = PhaseIdx.single_exc(det_i.beta, det_j.beta)
            yield (h1, h2, p1, p2), phaseA * phaseB

        ed_up, ed_dn = Excitation.exc_degree(det_i, det_j)
        # Same determinant -> Diagonal element
        if (ed_up, ed_dn) == (0, 0):
            yield from Hamiltonian_two_electrons_determinant_driven.H_ii_indices(det_i)
        # Single excitation
        elif (ed_up, ed_dn) == (1, 0):
            yield from H_ij_single_indices(det_i.alpha, det_j.alpha, det_i.beta)
        elif (ed_up, ed_dn) == (0, 1):
            yield from H_ij_single_indices(det_i.beta, det_j.beta, det_i.alpha)
        # Double excitation of same spin
        elif (ed_up, ed_dn) == (2, 0):
            yield from H_ij_doubleAA_indices(det_i.alpha, det_j.alpha)
        elif (ed_up, ed_dn) == (0, 2):
            yield from H_ij_doubleAA_indices(det_i.beta, det_j.beta)
        # Double excitation of opposite spins
        elif (ed_up, ed_dn) == (1, 1):
            yield from H_ij_doubleAB_2e_index(det_i, det_j)

    @staticmethod
    def H_indices(
        psi_internal: Psi_det, psi_j: Psi_det
    ) -> Iterator[Two_electron_integral_index_phase]:
        for a, det_i in enumerate(psi_internal):
            for b, det_j in enumerate(psi_j):
                for idx, phase in Hamiltonian_two_electrons_determinant_driven.H_ij_indices(
                    det_i, det_j
                ):
                    yield (a, b), idx, phase

    def H(self, psi_internal: Psi_det, psi_external: Psi_det) -> List[List[Energy]]:
        # det_external_to_index = {d: i for i, d in enumerate(psi_external)}
        # This is the function who will take foreever
        h = np.zeros(shape=(len(psi_internal), len(psi_external)))
        for (a, b), (i, j, k, l), phase in self.H_indices(psi_internal, psi_external):
            h[a, b] += phase * self.H_ijkl_orbital(i, j, k, l)
        return h

    def H_ii(self, det_i: Determinant):
        return sum(
            phase * self.H_ijkl_orbital(i, j, k, l)
            for (i, j, k, l), phase in self.H_ii_indices(det_i)
        )


#   ___            _
#    |       _    |_ |  _   _ _|_ ._ _  ._   _
#    | \/\/ (_)   |_ | (/_ (_  |_ | (_) | | _>
#   ___                           _
#    |  ._ _|_  _   _  ._ _. |   | \ ._ o     _  ._
#   _|_ | | |_ (/_ (_| | (_| |   |_/ |  | \/ (/_ | |
#                   _|


@dataclass
class Hamiltonian_two_electrons_integral_driven(object):
    d_two_e_integral: Two_electron_integral

    def H_ijkl_orbital(self, i: OrbitalIdx, j: OrbitalIdx, k: OrbitalIdx, l: OrbitalIdx) -> float:
        """Assume that *all* the integrals are in
        `d_two_e_integral` In this function, for simplicity we don't use any
        symmetry sparse representation.  For real calculations, symmetries and
        storing only non-zeros needs to be implemented to avoid an explosion of
        the memory requirements."""
        key = compound_idx4(i, j, k, l)
        return self.d_two_e_integral[key]

    @staticmethod
    def H_ii_indices(det_i: Determinant) -> Iterator[Two_electron_integral_index_phase]:
        """Diagonal element of the Hamiltonian : <I|H|I>.
        >>> sorted(Hamiltonian_two_electrons_integral_driven.H_ii_indices( Determinant((0,1),(2,3))))
        [((0, 1, 0, 1), 1), ((0, 1, 1, 0), -1), ((0, 2, 0, 2), 1), ((0, 3, 0, 3), 1),
         ((1, 2, 1, 2), 1), ((1, 3, 1, 3), 1), ((2, 3, 2, 3), 1), ((2, 3, 3, 2), -1)]
        """
        for i, j in combinations(det_i.alpha, 2):
            yield (i, j, i, j), 1
            yield (i, j, j, i), -1

        for i, j in combinations(det_i.beta, 2):
            yield (i, j, i, j), 1
            yield (i, j, j, i), -1

        for i, j in product(det_i.alpha, det_i.beta):
            yield (i, j, i, j), 1

    @staticmethod
    def get_dets_occ_in_orbitals(
        spindet_occ: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ: Dict[OrbitalIdx, Set[int]],
        d_orbitals: Dict[str, Set[OrbitalIdx]],
        which_orbitals,
    ):
        """
        Get indices of determinants that are occupied in the orbitals d_orbitals.
        Input which_orbitals = "all" or "any" indicates if we want dets occupied in all of the indices, or just any of the indices
        >>> Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals({0: {0}, 1: {0, 1}, 3: {1}}, {1: {0}, 2: {0}, 4: {1}, 5: {1}},  {"same": {0, 1}, "opposite": {}}, "all")
        {0}
        >>> Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals({0: {0}, 1: {0, 1}, 3: {1}}, {1: {0}, 2: {0}, 4: {1}, 5: {1}},  {"same": {0}, "opposite": {4}}, "all")
        set()
        """
        l = []
        for spintype, indices in d_orbitals.items():
            if spintype == "same":
                l += [spindet_occ[o] for o in indices]
            if spintype == "opposite":
                l += [oppspindet_occ[o] for o in indices]
        if which_orbitals == "all":
            return set.intersection(*l)
        else:
            return set.union(*l)

    @staticmethod
    def get_dets_via_orbital_occupancy(
        spindet_occ: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ: Dict[OrbitalIdx, Set[int]],
        d_occupied: Dict[str, Set[OrbitalIdx]],
        d_unoccupied: Dict[str, Set[OrbitalIdx]],
    ):
        """
        If psi_i == psi_j, return indices of determinants occupied in d_occupied and empty
        in d_unoccupied.
        >>> Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy({0: {0}, 1: {0, 1}, 3: {1}}, {}, {"same": {1}}, {"same": {0}})
        {1}
        >>> Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy({0: {0}, 1: {0, 1, 2}, 3: {1}}, {1: {0}, 2: {0}, 4: {1}, 5: {1}}, {"same": {1}, "opposite": {1}}, {"same": {3}})
        {0}
        """

        return Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
            spindet_occ, oppspindet_occ, d_occupied, "all"
        ) - Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
            spindet_occ, oppspindet_occ, d_unoccupied, "any"
        )

    @staticmethod
    def do_diagonal(det_indices, psi_i, det_to_index_j, phase):
        # contribution from integrals to diagonal elements
        for a in det_indices:
            # Handle PT2 case when psi_i != psi_j. In this case, psi_i[a] won't be in the external space and so error will be thrown
            try:
                J = det_to_index_j[psi_i[a]]
            except KeyError:
                pass
            else:
                yield (a, a), phase

    @staticmethod
    def do_single(det_indices_i, phasemod, occ, h, p, psi_i, det_to_index_j, spin, N_orb):
        # Single excitation from h to p, occ is index of orbital occupied
        # Excitation is from internal to external space
        for a in det_indices_i:  # Loop through candidate determinants in internal space
            det = psi_i[a]
            excited_spindet = Excitation(N_orb).apply_excitation(getattr(det, spin), [[h], [p]])
            if spin == "alpha":
                excited_det = Determinant(excited_spindet, getattr(det, "beta"))
            else:
                excited_det = Determinant(getattr(det, "alpha"), excited_spindet)
            try:  # Check if excited det is in external space
                J = det_to_index_j[excited_det]
            except KeyError:
                pass
            else:
                phase = phasemod * PhaseIdx.single_phase(getattr(det, spin), excited_spindet, h, p)
                yield (a, J), phase

    @staticmethod
    def do_double_samespin(
        hp1, hp2, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin, N_orb
    ):
        # hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        # double excitation from i to j and k to l, electrons are of the same spin
        i, k = hp1
        j, l = hp2
        det_indices_AA = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
            spindet_occ_i, {}, {"same": {i, j}}, {"same": {k, l}}
        )
        for a in det_indices_AA:  # Loop through candidate determinants in internal space
            det = psi_i[a]
            excited_spindet = Excitation(N_orb).apply_excitation(
                getattr(det, spin), [[i, j], [k, l]]
            )
            if spin == "alpha":
                excited_det = Determinant(excited_spindet, getattr(det, "beta"))
            else:
                excited_det = Determinant(getattr(det, "alpha"), excited_spindet)
            try:  # Check if excited det is in external space
                J = det_to_index_j[excited_det]
            except KeyError:
                pass
            else:
                phase = PhaseIdx.double_phase(getattr(det, spin), excited_spindet, i, j, k, l)
                yield (a, J), phase

    @staticmethod
    def do_double_oppspin(
        hp1, hp2, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin, N_orb
    ):
        # hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        # double excitation from i to j and k to l, electrons are of opposite spin spin
        i, k = hp1
        j, l = hp2
        det_indices_AB = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
            spindet_occ_i,
            oppspindet_occ_i,
            {"same": {i}, "opposite": {j}},
            {"same": {k}, "opposite": {l}},
        )
        for a in det_indices_AB:  # Look through candidate determinants in internal space
            det = psi_i[a]
            excited_spindet_A = Excitation(N_orb).apply_excitation(getattr(det, spin), [[i], [k]])
            phaseA = PhaseIdx.single_phase(getattr(det, spin), excited_spindet_A, i, k)
            if spin == "alpha":
                excited_spindet_B = Excitation(N_orb).apply_excitation(
                    getattr(det, "beta"), [[j], [l]]
                )
                phaseB = PhaseIdx.single_phase(getattr(det, "beta"), excited_spindet_B, j, l)
                excited_det = Determinant(excited_spindet_A, excited_spindet_B)
            else:
                excited_spindet_B = Excitation(N_orb).apply_excitation(
                    getattr(det, "alpha"), [[j], [l]]
                )
                phaseB = PhaseIdx.single_phase(getattr(det, "alpha"), excited_spindet_B, j, l)
                excited_det = Determinant(excited_spindet_B, excited_spindet_A)
            try:  # Check if excited det is in external space
                J = det_to_index_j[excited_det]
            except KeyError:
                pass
            else:
                yield (a, J), phaseA * phaseB

    @staticmethod
    def category_A(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category A, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i = j = k = 1: (1,1,1,1). This category will contribute to diagonal elements of the Hamiltonian matrix, only
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "A"

        def do_diagonal_A(i, j, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i):
            phase = 1
            # Get indices of determinants occupied in ia and ib
            det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                spindet_occ_i, oppspindet_occ_i, {"same": {i}, "opposite": {j}}, "all"
            )

            # phase is always 1
            yield from Hamiltonian_two_electrons_integral_driven.do_diagonal(
                det_indices, psi_i, det_to_index_j, 1
            )

        yield from do_diagonal_A(i, j, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)

    @staticmethod
    def category_B(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category B, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i = k < j = l: (1,2,1,2). This category will contribute to diagonal elements of the Hamiltonian matrix, only
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "B"

        def do_diagonal_B(i, j, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i):
            # Get indices of determinants occupied in ia and ja, jb and jb, ia and jb, and ib and ja
            det_indices = chain(
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i}, "opposite": {j}}, "all"
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, j}}, "all"
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    oppspindet_occ_i, spindet_occ_i, {"same": {i}, "opposite": {j}}, "all"
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    oppspindet_occ_i, spindet_occ_i, {"same": {i, j}}, "all"
                ),
            )

            # phase is always 1
            yield from Hamiltonian_two_electrons_integral_driven.do_diagonal(
                det_indices, psi_i, det_to_index_j, 1
            )

        yield from do_diagonal_B(i, j, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)

    @staticmethod
    def category_C(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category C, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i = k < j < l: (1,2,1,3), i < k < j = l: (1,3,2,3), j < i = k < l: (2,1,2,3)
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "C"

        # Hopefully, can remove hashes (det_to_index_i,j, psi_i,j, spindets... ) and call them as properties of the class (self. ...)
        def do_single_C(
            i, j, k, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin, N_orb
        ):
            # Get indices of determinants that are possibly related by excitations from internal --> external space
            # phasemod, occ, h, p = 1, j, i, k
            det_indices_1 = chain(
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, {}, {"same": {j, i}}, {"same": {k}}
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i}, "opposite": {j}}, {"same": {k}}
                ),
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_1, 1, j, i, k, psi_i, det_to_index_j, spin, N_orb
            )
            # Get indices of determinants that are possibly related by excitations from external --> internal space
            # phasemod, occ, h, p = 1, j, k, i
            det_indices_2 = chain(
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, {}, {"same": {j, k}}, {"same": {i}}
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {k}, "opposite": {j}}, {"same": {i}}
                ),
            )

            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_2, 1, j, k, i, psi_i, det_to_index_j, spin, N_orb
            )

        if i == k:  # <ij|il> = <ji|li>, ja(b) to la(b) where ia or ib is occupied
            yield from do_single_C(
                j,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_C(
                j,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )
        else:  # j == l, <ji|jk> = <ij|kj>, ia(b) to ka(b) where ja or jb or is occupied
            yield from do_single_C(
                i,
                j,
                k,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_C(
                i,
                j,
                k,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )

    @staticmethod
    def category_D(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category D, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i=j=k<l (1,1,1,2), i<j=k=l (1,2,2,2)
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "D"

        def do_single_D(
            i, j, l, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin, N_orb
        ):
            # phasemod, occ, h, p = 1, i, j, l
            det_indices_1 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {j}, "opposite": {i}}, {"same": {l}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_1, 1, i, j, l, psi_i, det_to_index_j, spin, N_orb
            )

            # phasemod, occ, h, p = 1, i, l, j
            det_indices_2 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {l}, "opposite": {i}}, {"same": {j}}
                )
            )

            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_2, 1, i, l, j, psi_i, det_to_index_j, spin, N_orb
            )

        if i == j:  # <ii|il>, ia(b) to la(b) while ib(a) is occupied
            yield from do_single_D(
                i,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_D(
                i,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )
        else:  # i < j == k == l, <ij|jj> = <jj|ij> = <jj|ji>, ja(b) to ia(b) where jb(a) is occupied
            yield from do_single_D(
                j,
                j,
                i,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_D(
                j,
                j,
                i,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )

    @staticmethod
    def category_E(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category E, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i=j<k<l (1,1,2,3), i<j=k<l (1,2,2,3), i<j<k=l (1,2,3,3)
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "E"

        def do_single_E(
            i, k, l, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin, N_orb
        ):
            # phasemod, occ, h, p = -1, i, k, l
            det_indices_1 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, k}}, {"same": {l}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_1, -1, i, k, l, psi_i, det_to_index_j, spin, N_orb
            )

            # phasemod, occ, h, p = -1, i, l, k
            det_indices_2 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, l}}, {"same": {k}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_2, -1, i, l, k, psi_i, det_to_index_j, spin, N_orb
            )

        # doubles, ia(b) to ka(b) and jb(a) to lb(a)
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta", N_orb
            )

        if i == j:  # <ii|kl> = <ii|lk> = <ik|li> -> - <ik|il>
            # singles, ka(b) to la(b) where ia(b) is occupied
            yield from do_single_E(
                i,
                k,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_E(
                i,
                k,
                l,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )
        elif j == k:  # <ij|jl> = - <ij|lj>
            # singles, ia(b) to la(b) where ja(b) is occupied
            yield from do_single_E(
                j,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_E(
                j,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )
        else:  # k == l, <ij|kk> = <ji|kk> = <jk|ki> -> -<jk|ik>
            # singles, ja(b) to ia(b) where ka(b) is occupied
            yield from do_single_E(
                k,
                i,
                j,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
                N_orb,
            )
            yield from do_single_E(
                k,
                i,
                j,
                psi_i,
                det_to_index_j,
                spindet_b_occ_i,
                spindet_a_occ_i,
                "beta",
                N_orb,
            )

    @staticmethod
    def category_F(
        idx,
        psi_i,
        det_to_index_j,
        spindet_a_occ_i,
        spindet_b_occ_i,
        N_orb,
    ):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category F, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i=j<k=l (1,1,2,2). Contributes to diagonal elements and doubles
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "F"

        def do_diagonal_F(i, k, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i):
            # should have negative phase, since <11|22> = <12|21> -> <12|12> with negative factor
            # Get indices of determinants occupied in ia, ja and jb, jb
            det_indices = chain(
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, k}}, "all"
                ),
                Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
                    oppspindet_occ_i, spindet_occ_i, {"same": {i, k}}, "all"
                ),
            )
            # phase is always -1
            yield from Hamiltonian_two_electrons_integral_driven.do_diagonal(
                det_indices, psi_i, det_to_index_j, -1
            )

        yield from do_diagonal_F(i, k, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)

        # Only call for a single spin variable. Each excitation involves ia, ib to ka, kb. Flipping the spin just double counts it
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [i, k], [i, k], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
        )
        # Need to do this twice, ia -> ka, kb -> ib, and ka -> ia, ib -> kb
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [i, k], [k, i], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
        )
        # Need to do this twice, ia -> ka, kb -> ib, and ka -> ia, ib -> kb
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [i, k], [k, i], psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta", N_orb
        )
        # Only call for a single spin variable. Each excitation involves ia, ib to ka, kb. Flipping the spin just double counts it
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [k, i], [k, i], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
        )

    @staticmethod
    def category_G(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb):
        """
        psi_i psi_j: Psi_det, lists of determinants
        idx: i,j,k,l, index of integral <ij|kl>
        For an integral i,j,k,l of category G, yield all dependent determinant pairs (I,J) and associated phase
        Possibilities are i<j<k<l (1,2,3,4), i<k<j<l (1,3,2,4), j<i<k<l (2,1,3,4)
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "G"

        # doubles, hp1 and hp2 are particle-hole pairs of each excitations
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta", N_orb
            )
        # doubles, hp1 and hp2 are particle-hole pairs of each excitations
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha", N_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta", N_orb
            )

    @staticmethod
    def get_spindet_a_occ_spindet_b_occ(
        psi_i: Psi_det,
    ) -> Tuple[Dict[OrbitalIdx, Set[int]], Dict[OrbitalIdx, Set[int]]]:
        """
        maybe use dict with spin as key instead of tuple?
        >>> Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ([Determinant(alpha=(0,1),beta=(1,2)),Determinant(alpha=(1,3),beta=(4,5))])
        (defaultdict(<class 'set'>, {0: {0}, 1: {0, 1}, 3: {1}}),
         defaultdict(<class 'set'>, {1: {0}, 2: {0}, 4: {1}, 5: {1}}))
        >>> Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ([Determinant(alpha=(0,),beta=(0,))])[0][1]
        set()
        """
        # Can generate det_to_indices hash in here
        def get_dets_occ(psi_i: Psi_det, spin: str) -> Dict[OrbitalIdx, Set[int]]:
            ds = defaultdict(set)
            for i, det in enumerate(psi_i):
                for o in getattr(det, spin):
                    ds[o].add(i)
            return ds

        return tuple(get_dets_occ(psi_i, spin) for spin in ["alpha", "beta"])

    @cached_property
    def integral_by_category(self):
        # Bin each integral (with the 'idx4' representation) by integrals category
        d = defaultdict(list)
        for idx in self.d_two_e_integral:
            i, j, k, l = compound_idx4_reverse(idx)
            cat = integral_category(i, j, k, l)
            d[cat].append((i, j, k, l))
        return d

    @cached_property
    def N_orb(self):
        key = max(self.d_two_e_integral)
        return max(compound_idx4_reverse(key)) + 1

    def H_indices(self, psi_i, psi_j) -> Iterator[Two_electron_integral_index_phase]:
        # Returns H_indices, and idx of associated integral
        spindet_a_occ_i, spindet_b_occ_i = self.get_spindet_a_occ_spindet_b_occ(psi_i)
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}

        for idx4, integral_values in self.d_two_e_integral.items():
            idx = compound_idx4_reverse(idx4)
            for (
                (a, b),
                phase,
            ) in self.H_indices_idx(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i):
                yield (a, b), idx, phase

    def H_indices_idx(
        self, idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i
    ) -> Iterator[Two_electron_integral_index_phase]:
        category = integral_category(*idx)
        if category == "A":
            yield from Hamiltonian_two_electrons_integral_driven.category_A(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i
            )
        if category == "B":
            yield from Hamiltonian_two_electrons_integral_driven.category_B(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i
            )
        if category == "C":
            yield from Hamiltonian_two_electrons_integral_driven.category_C(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "D":
            yield from Hamiltonian_two_electrons_integral_driven.category_D(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "E":
            yield from Hamiltonian_two_electrons_integral_driven.category_E(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "F":
            yield from Hamiltonian_two_electrons_integral_driven.category_F(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "G":
            yield from Hamiltonian_two_electrons_integral_driven.category_G(
                idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )

    def H(self, psi_i, psi_j) -> List[List[Energy]]:
        # Can optimize having to compute these each H call
        spindet_a_occ_i, spindet_b_occ_i = self.get_spindet_a_occ_spindet_b_occ(psi_i)
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        # This is the function who will take foreever
        h = np.zeros(shape=(len(psi_i), len(psi_j)))
        for idx4, integral_values in self.d_two_e_integral.items():
            idx = compound_idx4_reverse(idx4)
            for (
                (a, b),
                phase,
            ) in self.H_indices_idx(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i):
                h[a, b] += phase * integral_values
        return h

    def H_ii(self, det_i: Determinant):
        return sum(phase * self.H_ijkl_orbital(*idx) for idx, phase in self.H_ii_indices(det_i))


@dataclass
class Hamiltonian(object):
    """
    Now, we consider the Hamiltonian matrix in the basis of Slater determinants.
    Slater-Condon rules are used to compute the matrix elements <I|H|J> where I
    and J are Slater determinants.

     ~
     Slater-Condon Rules
     ~

     https://en.wikipedia.org/wiki/Slater%E2%80%93Condon_rules
     https://arxiv.org/abs/1311.6244

     * H is symmetric
     * If I and J differ by more than 2 orbitals, <I|H|J> = 0, so the number of
       non-zero elements of H is bounded by N_det x ( N_alpha x (n_orb - N_alpha))^2,
       where N_det is the number of determinants, N_alpha is the number of
       alpha-spin electrons (N_alpha >= N_beta), and n_orb is the number of
       molecular orbitals.  So the number of non-zero elements scales linearly with
       the number of selected determinant.
    """

    d_one_e_integral: One_electron_integral
    d_two_e_integral: Two_electron_integral
    E0: Energy
    driven_by: str = "determinant"

    @cached_property
    def H_one_electron(self):
        return Hamiltonian_one_electron(self.d_one_e_integral, self.E0)

    @cached_property
    def H_two_electrons(self):
        if self.driven_by == "determinant":
            return Hamiltonian_two_electrons_determinant_driven(self.d_two_e_integral)
        elif self.driven_by == "integral":
            return Hamiltonian_two_electrons_integral_driven(self.d_two_e_integral)
        else:
            raise NotImplementedError

    # ~ ~ ~
    # H_ii
    # ~ ~ ~
    def H_ii(self, det_i: Determinant) -> List[Energy]:
        return self.H_one_electron.H_ii(det_i) + self.H_two_electrons.H_ii(det_i)

    # ~ ~ ~
    # H
    # ~ ~ ~
    def H(self, psi_internal: Psi_det, psi_external: Psi_det = None) -> List[List[Energy]]:
        """Return a matrix of size psi x psi_j containing the value of the Hamiltonian.
        If psi_j == None, then assume a return psi x psi hermitian Hamiltonian,
        if not not overlap exist between psi and psi_j"""
        if psi_external is None:
            psi_external = psi_internal

        return self.H_one_electron.H(psi_internal, psi_external) + self.H_two_electrons.H(
            psi_internal, psi_external
        )


#  _                  _
# |_) _        _  ._ |_) |  _. ._ _|_
# |  (_) \/\/ (/_ |  |   | (_| | | |_
#
@dataclass
class Powerplant(object):
    """
    Compute all the Energy and associated value from a psi_det.
    E denote the variational energy
    """

    lewis: Hamiltonian
    psi_det: Psi_det

    def E(self, psi_coef: Psi_coef) -> Energy:
        # Vector * Vector.T * Matrix
        return np.einsum("i,j,ij ->", psi_coef, psi_coef, self.lewis.H(self.psi_det))

    @property
    def E_and_psi_coef(self) -> Tuple[Energy, Psi_coef]:
        # Return lower eigenvalue (aka the new E) and lower evegenvector (aka the new psi_coef)
        psi_H_psi = self.lewis.H(self.psi_det)
        energies, coeffs = np.linalg.eigh(psi_H_psi)
        return energies[0], coeffs[:, 0]

    def psi_external_pt2(self, psi_coef: Psi_coef, n_orb) -> Tuple[Psi_det, List[Energy]]:
        # Compute the pt2 contrution of all the external (aka connected) determinant.
        #   eα=⟨Ψ(n)∣H∣∣α⟩^2 / ( E(n)−⟨α∣H∣∣α⟩ )
        psi_external = Excitation(n_orb).gen_all_connected_determinant(self.psi_det)

        nomitator = np.einsum(
            "i,ij -> j", psi_coef, self.lewis.H(self.psi_det, psi_external)
        )  # vector * Matrix -> vector
        denominator = np.divide(
            1.0, self.E(psi_coef) - np.array([self.lewis.H_ii(d) for d in psi_external])
        )

        return psi_external, np.einsum(
            "i,i,i -> i", nomitator, nomitator, denominator
        )  # vector * vector * vector -> scalar

    def E_pt2(self, psi_coef: Psi_coef, n_orb) -> Energy:
        # The sum of the pt2 contribution of each external determinant
        _, psi_external_energy = self.psi_external_pt2(psi_coef, n_orb)
        return sum(psi_external_energy)


#  __
# (_   _  |  _   _ _|_ o  _  ._
# __) (/_ | (/_ (_  |_ | (_) | |
#
def selection_step(
    lewis: Hamiltonian, n_ord, psi_coef: Psi_coef, psi_det: Psi_det, n
) -> Tuple[Energy, Psi_coef, Psi_det]:
    # 1. Generate a list of all the external determinant and their pt2 contribution
    # 2. Take the n  determinants who have the biggest contribution and add it the wave function psi
    # 3. Diagonalize H corresponding to this new wave function to get the new variational energy, and new psi_coef.

    # In the main code:
    # -> Go to 1., stop when E_pt2 < Threshold || N < Threshold
    # See example of chained call to this function in `test_f2_631g_1p5p5det`

    # 1.
    psi_external_det, psi_external_energy = Powerplant(lewis, psi_det).psi_external_pt2(
        psi_coef, n_ord
    )

    # 2.
    idx = np.argpartition(psi_external_energy, n)[:n]
    psi_det_extented = psi_det + [psi_external_det[i] for i in idx]

    # 3.
    return (*Powerplant(lewis, psi_det_extented).E_and_psi_coef, psi_det_extented)


#   _____         _   _
#  |_   _|       | | (_)
#    | | ___  ___| |_ _ _ __   __ _
#    | |/ _ \/ __| __| | '_ \ / _` |
#    | |  __/\__ \ |_| | | | | (_| |
#    \_/\___||___/\__|_|_| |_|\__, |
#                              __/ |
#                             |___/
import unittest
import time


class Timing:
    def setUp(self):
        print(f"{self.id()} ... ", end="", flush=True)
        self.startTime = time.perf_counter()
        if PROFILING:
            import cProfile

            self.pr = cProfile.Profile()
            self.pr.enable()

    def tearDown(self):
        t = time.perf_counter() - self.startTime
        print(f"ok ({t:.3f}s)")
        if PROFILING:
            from pstats import Stats

            self.pr.disable()
            p = Stats(self.pr)
            p.strip_dirs().sort_stats("tottime").print_stats(0.05)


class Test_Index(Timing, unittest.TestCase):
    def test_idx2_reverse(self, n=10000, nmax=(1 << 63) - 1):
        def check_idx2_reverse(ij):
            i, j = compound_idx2_reverse(ij)
            self.assertTrue(i <= j)
            self.assertEqual(ij, compound_idx2(i, j))

        for ij in random.sample(range(nmax), k=n):
            check_idx2_reverse(ij)

    def test_idx4_reverse(self, n=10000, nmax=(1 << 63) - 1):
        def check_idx4_reverse(ijkl):
            i, j, k, l = compound_idx4_reverse(ijkl)
            ik = compound_idx2(i, k)
            jl = compound_idx2(j, l)
            self.assertTrue(i <= k)
            self.assertTrue(j <= l)
            self.assertTrue(ik <= jl)
            self.assertEqual(ijkl, compound_idx4(i, j, k, l))

        for ijkl in random.sample(range(nmax), k=n):
            check_idx4_reverse(ijkl)

    def test_idx4_reverse_all(self, n=10000, nmax=(1 << 63) - 1):
        def check_idx4_reverse_all(ijkl):
            for i, j, k, l in compound_idx4_reverse_all(ijkl):
                self.assertEqual(compound_idx4(i, j, k, l), ijkl)

        for ijkl in random.sample(range(nmax), k=n):
            check_idx4_reverse_all(ijkl)

    def test_canonical_idx4(self, n=10000, nmax=(1 << 63) - 1):
        def check_canonical_idx4(ijkl):
            for i, j, k, l in compound_idx4_reverse_all(ijkl):
                self.assertEqual(
                    canonical_idx4(*compound_idx4_reverse(ijkl)), canonical_idx4(i, j, k, l)
                )

        for ijkl in random.sample(range(nmax), k=n):
            check_canonical_idx4(ijkl)

    def test_compound_idx4_reverse_is_canonical(self, n=10000, nmax=(1 << 63) - 1):
        def check_compound_idx4_reverse_is_canonical(ijkl):
            self.assertEqual(
                compound_idx4_reverse(ijkl), canonical_idx4(*compound_idx4_reverse(ijkl))
            )

        for ijkl in random.sample(range(nmax), k=n):
            check_compound_idx4_reverse_is_canonical(ijkl)


class Test_Category:
    def check_pair_idx_A(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "A")
        i, _, _, _ = idx
        self.assertEqual((i, i, i, i), idx)
        self.assertEqual(da, db)
        self.assertIn(i, da.alpha)
        self.assertIn(i, da.beta)

    def check_pair_idx_B(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "B")
        i, j, _, _ = idx
        self.assertEqual((i, j, i, j), idx)
        self.assertEqual(da, db)
        self.assertIn(i, da.alpha + da.beta)
        self.assertIn(j, da.alpha + da.beta)

    def check_pair_idx_C(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "C")
        i, j, k, l = idx
        exc = Excitation.exc_degree(da, db)
        self.assertIn(exc, ((1, 0), (0, 1)))
        if exc == (1, 0):
            (dsa, _), (dsb, _) = da, db
        elif exc == (0, 1):
            (_, dsa), (_, dsb) = da, db
        h, p = PhaseIdx.single_exc_no_phase(dsa, dsb)
        self.assertTrue(j == l or i == k)
        if j == l:
            self.assertEqual(sorted((h, p)), sorted((i, k)))
            self.assertIn(j, da.alpha + da.beta)
            self.assertIn(j, db.alpha + db.beta)
        elif i == k:
            self.assertEqual(sorted((h, p)), sorted((j, l)))
            self.assertIn(i, da.alpha + da.beta)
            self.assertIn(i, db.alpha + db.beta)

    def check_pair_idx_D(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "D")
        i, j, k, l = idx
        exc = Excitation.exc_degree(da, db)
        self.assertIn(exc, ((1, 0), (0, 1)))
        if exc == (1, 0):
            (dsa, dta), (dsb, dtb) = da, db
        elif exc == (0, 1):
            (dta, dsa), (dtb, dsb) = da, db
        h, p = PhaseIdx.single_exc_no_phase(dsa, dsb)
        self.assertTrue(j == l or i == k)
        if j == l:
            self.assertEqual(sorted((h, p)), sorted((i, k)))
            self.assertIn(j, dta)
            self.assertIn(j, dtb)
        elif i == k:
            self.assertEqual(sorted((h, p)), sorted((j, l)))
            self.assertIn(i, dta)
            self.assertIn(i, dtb)

    def check_pair_idx_E(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "E")
        i, j, k, l = idx
        self.assertTrue(i == j or j == k or k == l)
        exc = Excitation.exc_degree(da, db)
        self.assertIn(exc, ((1, 0), (0, 1), (1, 1)))
        if exc == (1, 1):
            (dsa, dta), (dsb, dtb) = da, db
            if i == j:
                p, r, s = i, k, l
            elif j == k:
                p, r, s = j, i, l
            elif k == l:
                p, r, s = k, j, i
            hs, ps = PhaseIdx.single_exc_no_phase(dsa, dsb)
            ht, pt = PhaseIdx.single_exc_no_phase(dta, dtb)
            self.assertEqual(
                sorted((sorted((hs, ps)), sorted((ht, pt)))),
                sorted((sorted((p, r)), sorted((p, s)))),
            )
        else:  # exc in ((1,0),(0,1))
            if exc == (1, 0):
                (dsa, _), (dsb, _) = da, db
            elif exc == (0, 1):
                (_, dsa), (_, dsb) = da, db
            h, p = PhaseIdx.single_exc_no_phase(dsa, dsb)
            if i == j:
                self.assertEqual(sorted((h, p)), sorted((k, l)))
                self.assertIn(i, dsa)
                self.assertIn(i, dsb)
            elif j == k:
                self.assertEqual(sorted((h, p)), sorted((i, l)))
                self.assertIn(j, dsa)
                self.assertIn(j, dsb)
            elif k == l:
                self.assertEqual(sorted((h, p)), sorted((i, j)))
                self.assertIn(k, dsa)
                self.assertIn(k, dsb)

    def check_pair_idx_F(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "F")
        i, _, k, _ = idx
        exc = Excitation.exc_degree(da, db)
        self.assertIn(exc, ((0, 0), (1, 1)))
        if exc == (0, 0):
            self.assertEqual(da, db)
            self.assertTrue(
                ((i in da.alpha) and (k in da.alpha)) or ((i in da.beta) and (k in da.beta))
            )
        elif exc == (1, 1):
            (dsa, dta), (dsb, dtb) = da, db
            hs, ps = PhaseIdx.single_exc_no_phase(dsa, dsb)
            ht, pt = PhaseIdx.single_exc_no_phase(dta, dtb)
            self.assertEqual(sorted((hs, ps)), sorted((i, k)))
            self.assertEqual(sorted((ht, pt)), sorted((i, k)))

    def check_pair_idx_G(self, dadb, idx):
        da, db = dadb
        self.assertEqual(integral_category(*idx), "G")
        i, j, k, l = idx
        exc = Excitation.exc_degree(da, db)
        self.assertIn(exc, ((1, 1), (2, 0), (0, 2)))
        if exc == (1, 1):
            (dsa, dta), (dsb, dtb) = da, db
            hs, ps = PhaseIdx.single_exc_no_phase(dsa, dsb)
            ht, pt = PhaseIdx.single_exc_no_phase(dta, dtb)
            self.assertEqual(
                sorted((sorted((hs, ps)), sorted((ht, pt)))),
                sorted((sorted((i, k)), sorted((j, l)))),
            )
        else:
            if exc == (2, 0):
                (dsa, _), (dsb, _) = da, db
            elif exc == (0, 2):
                (_, dsa), (_, dsb) = da, db
            h1, h2, p1, p2 = PhaseIdx.double_exc_no_phase(dsa, dsb)
            self.assertIn(
                sorted((sorted((h1, h2)), sorted((p1, p2)))),
                (
                    sorted((sorted((i, j)), sorted((k, l)))),
                    sorted((sorted((i, l)), sorted((k, j)))),
                ),
            )


class Test_Minimal(Timing, unittest.TestCase, Test_Category):
    @staticmethod
    def simplify_indices(l):
        d = defaultdict(int)
        for (a, b), idx, phase in l:
            key = ((a, b), compound_idx4(*idx))
            d[key] += phase
        return sorted((ab, idx, phase) for (ab, idx), phase in d.items() if phase)

    @property
    def psi_and_integral(self):
        # 4 Electron in 4 Orbital
        # I'm stupid so let's do the product
        psi = [Determinant((0, 1), (0, 1))]
        psi += Excitation(4).gen_all_connected_determinant(psi)
        self.assertEqual(len(psi), 27)
        d_two_e_integral = {}
        for (i, j, k, l) in product(range(4), repeat=4):
            d_two_e_integral[compound_idx4(i, j, k, l)] = 1
        return psi, d_two_e_integral

    @property
    def psi_and_integral_PT2(self):
        # minimal psi_and_integral, psi_i != psi_j
        psi_i = [Determinant((0, 1), (0, 1)), Determinant((1, 2), (1, 2))]
        psi_j = Excitation(4).gen_all_connected_determinant(psi_i)
        #        self.assertEqual(len(psi_j), 26)
        _, d_two_e_integral = self.psi_and_integral
        return psi_i, psi_j, d_two_e_integral

    def test_equivalence(self):
        # Does `integral` and `determinant` driven produce the same H
        psi, d_two_e_integral = self.psi_and_integral

        h = Hamiltonian_two_electrons_determinant_driven(d_two_e_integral)
        determinant_driven_indices = self.simplify_indices(h.H_indices(psi, psi))

        h = Hamiltonian_two_electrons_integral_driven(d_two_e_integral)
        integral_driven_indices = self.simplify_indices(h.H_indices(psi, psi))
        self.assertListEqual(determinant_driven_indices, integral_driven_indices)

    def test_equivalence_PT2(self):
        # Does `integral` and `determinant` driven produce the same H in the case where psi_i != psi_j
        # Test integral-driven matrix construction in case of PT2
        psi_i, psi_j, d_two_e_integral = self.psi_and_integral_PT2

        h = Hamiltonian_two_electrons_determinant_driven(d_two_e_integral)
        determinant_driven_indices = self.simplify_indices(h.H_indices(psi_i, psi_j))

        h = Hamiltonian_two_electrons_integral_driven(d_two_e_integral)
        integral_driven_indices = self.simplify_indices(h.H_indices(psi_i, psi_j))
        self.assertListEqual(determinant_driven_indices, integral_driven_indices)

    def test_category(self):
        # Does the assumtion of your Ingral category holds
        psi, d_two_e_integral = self.psi_and_integral
        h = Hamiltonian_two_electrons_integral_driven(d_two_e_integral)
        integral_driven_indices = self.simplify_indices(h.H_indices(psi, psi))
        for (a, b), idx, phase in integral_driven_indices:
            i, j, k, l = compound_idx4_reverse(idx)
            category = integral_category(i, j, k, l)
            getattr(self, f"check_pair_idx_{category}")((psi[a], psi[b]), (i, j, k, l))


class Test_Integral_Driven_Categories(Test_Minimal):
    @property
    def integral_by_category(self):
        # Bin each integral (with the 'idx4' representation) by integrals category
        """
        >>> Test_Integral_Driven_Categories().integral_by_category['A']
        [(0, 0, 0, 0), (1, 1, 1, 1), (2, 2, 2, 2), (3, 3, 3, 3)]
        """
        psi, d_two_e_integral = self.psi_and_integral
        d = defaultdict(list)
        for idx in d_two_e_integral:
            i, j, k, l = compound_idx4_reverse(idx)
            cat = integral_category(i, j, k, l)
            d[cat].append((i, j, k, l))
        return d

    @property
    def reference_indices_by_category(self):
        # Bin the indices (ab, idx4, phase) of the reference determinant implemetation by integrals category
        """
        >>> len(Test_Integral_Driven_Categories().reference_indices_by_category['C'])
        264
        """
        psi, _ = self.psi_and_integral
        indices = Hamiltonian_two_electrons_determinant_driven.H_indices(psi, psi)
        d = defaultdict(list)
        for ab, (i, j, k, l), phase in indices:
            p, q, r, s = canonical_idx4(i, j, k, l)
            cat = integral_category(p, q, r, s)
            d[cat].append((ab, (p, q, r, s), phase))

        for k in d:
            d[k] = self.simplify_indices(d[k])
        return d

    @property
    def reference_indices_by_category_PT2(self):
        # Bin the indices (ab, idx4, phase) of the reference determinant implemetation by integrals category
        """
        >>> len(Test_Integral_Driven_Categories().reference_indices_by_category['C'])
        264
        """
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        indices = Hamiltonian_two_electrons_determinant_driven.H_indices(psi_i, psi_j)
        d = defaultdict(list)
        for ab, (i, j, k, l), phase in indices:
            p, q, r, s = canonical_idx4(i, j, k, l)
            cat = integral_category(p, q, r, s)
            d[cat].append((ab, (p, q, r, s), phase))

        for k in d:
            d[k] = self.simplify_indices(d[k])
        return d

    def test_category_A(self):
        psi, _ = self.psi_and_integral
        indices = []
        det_to_index = {det: i for i, det in enumerate(psi)}
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["A"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_A(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["A"])

    def test_category_A_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["A"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_A(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, [])

    def test_category_B(self):
        psi, _ = self.psi_and_integral
        indices = []
        det_to_index = {det: i for i, det in enumerate(psi)}
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["B"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_B(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["B"])

    def test_category_B_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["B"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_B(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, [])

    def test_category_C(self):
        psi, _ = self.psi_and_integral
        det_to_index = {det: i for i, det in enumerate(psi)}
        indices = []
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["C"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_C(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ, N_orb=4
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["C"])

    def test_category_C_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["C"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_C(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb=4
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, self.reference_indices_by_category_PT2["C"])

    def test_category_D(self):
        psi, _ = self.psi_and_integral
        det_to_index = {det: i for i, det in enumerate(psi)}
        indices = []
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["D"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_D(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ, N_orb=4
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["D"])

    def test_category_D_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["D"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_D(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb=4
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, self.reference_indices_by_category_PT2["D"])

    def test_category_E(self):
        psi, _ = self.psi_and_integral
        det_to_index = {det: i for i, det in enumerate(psi)}
        indices = []
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["E"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_E(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ, N_orb=4
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["E"])

    def test_category_E_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["E"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_E(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb=4
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, self.reference_indices_by_category_PT2["E"])

    def test_category_F(self):
        psi, _ = self.psi_and_integral
        det_to_index = {det: i for i, det in enumerate(psi)}
        indices = []
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["F"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_F(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ, N_orb=4
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["F"])

    def test_category_F_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["F"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_F(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb=4
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, self.reference_indices_by_category_PT2["F"])

    def test_category_G(self):
        psi, _ = self.psi_and_integral
        det_to_index = {det: i for i, det in enumerate(psi)}
        indices = []
        (
            spindet_a_occ,
            spindet_b_occ,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi)
        for (i, j, k, l) in self.integral_by_category["G"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_G(
                (i, j, k, l), psi, det_to_index, spindet_a_occ, spindet_b_occ, N_orb=4
            ):
                indices.append(((a, b), (i, j, k, l), phase))
        indices = self.simplify_indices(indices)
        self.assertListEqual(indices, self.reference_indices_by_category["G"])

    def test_category_G_PT2(self):
        psi_i, psi_j, _ = self.psi_and_integral_PT2
        det_to_index_j = {det: i for i, det in enumerate(psi_j)}
        indices_PT2 = []
        (
            spindet_a_occ_i,
            spindet_b_occ_i,
        ) = Hamiltonian_two_electrons_integral_driven.get_spindet_a_occ_spindet_b_occ(psi_i)
        for (i, j, k, l) in self.integral_by_category["G"]:
            for (a, b), phase in Hamiltonian_two_electrons_integral_driven.category_G(
                (i, j, k, l), psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, N_orb=4
            ):
                indices_PT2.append(((a, b), (i, j, k, l), phase))
        indices_PT2 = self.simplify_indices(indices_PT2)
        self.assertListEqual(indices_PT2, self.reference_indices_by_category_PT2["G"])


class Test_VariationalPowerplant:
    def test_c2_eq_dz_3(self):
        fcidump_path = "c2_eq_hf_dz.fcidump*"
        wf_path = "c2_eq_hf_dz_3.*.wf*"
        E_ref = load_eref("data/c2_eq_hf_dz_3.*.ref*")
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_c2_eq_dz_4(self):
        fcidump_path = "c2_eq_hf_dz.fcidump*"
        wf_path = "c2_eq_hf_dz_4.*.wf*"
        E_ref = load_eref("data/c2_eq_hf_dz_4.*.ref*")
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_1det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.1det.wf"
        E_ref = -198.646096743145
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_10det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.10det.wf"
        E_ref = -198.548963
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_30det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.30det.wf"
        E_ref = -198.738780989106
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_161det(self):
        fcidump_path = "f2_631g.161det.fcidump"
        wf_path = "f2_631g.161det.wf"
        E_ref = -198.8084269796
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_296det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.296det.wf"
        E_ref = -198.682736076007
        E = self.load_and_compute(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)


def load_and_compute(fcidump_path, wf_path, driven_by):
    # Load integrals
    n_ord, E0, d_one_e_integral, d_two_e_integral = load_integrals(f"data/{fcidump_path}")
    # Load wave function
    psi_coef, psi_det = load_wf(f"data/{wf_path}")
    # Computation of the Energy of the input wave function (variational energy)
    lewis = Hamiltonian(d_one_e_integral, d_two_e_integral, E0, driven_by)
    return Powerplant(lewis, psi_det).E(psi_coef)


class Test1_VariationalPowerplant_Determinant(
    Timing, unittest.TestCase, Test_VariationalPowerplant
):
    def load_and_compute(self, fcidump_path, wf_path):
        return load_and_compute(fcidump_path, wf_path, "determinant")


class Test1_VariationalPowerplant_Integral(Timing, unittest.TestCase, Test_VariationalPowerplant):
    def load_and_compute(self, fcidump_path, wf_path):
        return load_and_compute(fcidump_path, wf_path, "integral")


class Test_VariationalPT2Powerplant:
    def test_f2_631g_1det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.1det.wf"
        E_ref = -0.367587988032339
        E = self.load_and_compute_pt2(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_2det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.2det.wf"
        E_ref = -0.253904406461572
        E = self.load_and_compute_pt2(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_10det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.10det.wf"
        E_ref = -0.24321128
        E = self.load_and_compute_pt2(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_28det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.28det.wf"
        E_ref = -0.244245625775444
        E = self.load_and_compute_pt2(fcidump_path, wf_path)
        self.assertAlmostEqual(E_ref, E, places=6)


def load_and_compute_pt2(fcidump_path, wf_path, driven_by):
    # Load integrals
    n_ord, E0, d_one_e_integral, d_two_e_integral = load_integrals(f"data/{fcidump_path}")
    # Load wave function
    psi_coef, psi_det = load_wf(f"data/{wf_path}")
    # Computation of the Energy of the input wave function (variational energy)
    lewis = Hamiltonian(d_one_e_integral, d_two_e_integral, E0, driven_by)
    return Powerplant(lewis, psi_det).E_pt2(psi_coef, n_ord)


class Test_VariationalPT2_Determinant(Timing, unittest.TestCase, Test_VariationalPT2Powerplant):
    def load_and_compute_pt2(self, fcidump_path, wf_path):
        return load_and_compute_pt2(fcidump_path, wf_path, "determinant")


class Test_VariationalPT2_Integral(Timing, unittest.TestCase, Test_VariationalPT2Powerplant):
    def load_and_compute_pt2(self, fcidump_path, wf_path):
        return load_and_compute_pt2(fcidump_path, wf_path, "integral")


class TestSelection(unittest.TestCase):
    def load(self, fcidump_path, wf_path):
        # Load integrals
        n_ord, E0, d_one_e_integral, d_two_e_integral = load_integrals(f"data/{fcidump_path}")
        # Load wave function
        psi_coef, psi_det = load_wf(f"data/{wf_path}")
        return (
            n_ord,
            psi_coef,
            psi_det,
            Hamiltonian(d_one_e_integral, d_two_e_integral, E0),
        )

    def test_f2_631g_1p0det(self):
        # Verify that selecting 0 determinant is egual that computing the variational energy
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.1det.wf"

        n_ord, psi_coef, psi_det, lewis = self.load(fcidump_path, wf_path)
        E_var = Powerplant(lewis, psi_det).E(psi_coef)

        E_selection, _, _ = selection_step(lewis, n_ord, psi_coef, psi_det, 0)

        self.assertAlmostEqual(E_var, E_selection, places=6)

    def test_f2_631g_1p10det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.1det.wf"
        # No a value optained with QP
        E_ref = -198.72696793971556
        # Selection 10 determinant and check if the result make sence

        n_ord, psi_coef, psi_det, lewis = self.load(fcidump_path, wf_path)
        E, _, _ = selection_step(lewis, n_ord, psi_coef, psi_det, 10)

        self.assertAlmostEqual(E_ref, E, places=6)

    def test_f2_631g_1p5p5det(self):
        fcidump_path = "f2_631g.FCIDUMP"
        wf_path = "f2_631g.1det.wf"
        # We will select 5 determinant, than 5 more.
        # The value is lower than the one optained by selecting 10 deterinant in one go.
        # Indeed, the pt2 get more precise whith the number of selection
        E_ref = -198.73029308564543

        n_ord, psi_coef, psi_det, lewis = self.load(fcidump_path, wf_path)
        _, psi_coef, psi_det = selection_step(lewis, n_ord, psi_coef, psi_det, 5)
        E, psi_coef, psi_det = selection_step(lewis, n_ord, psi_coef, psi_det, 5)

        self.assertAlmostEqual(E_ref, E, places=6)


if __name__ == "__main__":
    import doctest
    import sys

    try:
        sys.argv.remove("--doctest-raise")
    except ValueError:
        DOCTEST_RAISE = False
    else:
        DOCTEST_RAISE = True
    try:
        sys.argv.remove("--profiling")
    except ValueError:
        PROFILING = False
    else:
        PROFILING = True
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE, raise_on_error=DOCTEST_RAISE)
    unittest.main(failfast=True, verbosity=0)
