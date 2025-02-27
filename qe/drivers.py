# Yes, I like itertools
from dataclasses import dataclass
from itertools import chain, product, combinations, takewhile, permutations, accumulate
from functools import partial, cached_property, cache
from collections import defaultdict
import numpy as np

# Import mpi4py and utilities
from mpi4py import MPI  # Note this initializes and finalizes MPI session automatically

from qe.fundamental_types import (
    Determinant,
    Psi_det,
    OrbitalIdx,
    Energy,
    Psi_coef,
    One_electron_integral,
    Two_electron_integral,
    Two_electron_integral_index,
    Two_electron_integral_index_phase,
)
from typing import Iterator, Set, Tuple, List, Dict
from qe.integral_indexing_utils import compound_idx4_reverse, compound_idx4, canonical_idx4

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

        def H_ij_spindet(sdet_j, spin: str) -> Energy:
            """<I|H|J>, when I and J differ by exactly one orbital."""
            # det_i is accessible
            phase, m, p = det_i.single_exc(sdet_j, spin)
            return self.H_ij_orbital(m, p) * phase

        ed_up, ed_dn = det_i.exc_degree(det_j)
        # Same determinant -> Diagonal element
        if (ed_up, ed_dn) == (0, 0):
            return self.H_ii(det_i)
        # Single excitation
        elif (ed_up, ed_dn) == (1, 0):
            return H_ij_spindet(det_j.alpha, "alpha")
        elif (ed_up, ed_dn) == (0, 1):
            return H_ij_spindet(det_j.beta, "beta")
        else:
            return 0.0

    def H(self, psi_i, psi_j) -> List[List[Energy]]:
        h = np.array([self.H_ij(det_i, det_j) for det_i, det_j in product(psi_i, psi_j)])
        return h.reshape(len(psi_i), len(psi_j))


#   _   _                 _ _ _              _
#  | | | |               (_) | |            (_)
#  | |_| | __ _ _ __ ___  _| | |_ ___  _ __  _  __ _ _ __
#  |  _  |/ _` | '_ ` _ \| | | __/ _ \| '_ \| |/ _` | '_ \
#  | | | | (_| | | | | | | | | || (_) | | | | | (_| | | | |
#  \_| |_/\__,_|_| |_| |_|_|_|\__\___/|_| |_|_|\__,_|_| |_|
#
#
#   ___            _
#    |       _    |_ |  _   _ _|_ ._ _  ._   _
#    | \/\/ (_)   |_ | (/_ (_  |_ | (_) | | _>
#


@dataclass
class Hamiltonian_two_electrons(object):
    """Put some things here that are used by both the determinant-driven and integral-driven
    versions of the code."""

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

    @cached_property
    def N_orb(self):
        key = max(self.d_two_e_integral)
        return max(compound_idx4_reverse(key)) + 1

    def H_ii(self, det_i: Determinant):
        return sum(phase * self.H_ijkl_orbital(*idx) for idx, phase in self.H_ii_indices(det_i))


#   ___            _
#    |       _    |_ |  _   _ _|_ ._ _  ._   _
#    | \/\/ (_)   |_ | (/_ (_  |_ | (_) | | _>
#    _                                          _
#   | \  _ _|_  _  ._ ._ _  o ._   _. ._ _|_   | \ ._ o     _  ._
#   |_/ (/_ |_ (/_ |  | | | | | | (_| | | |_   |_/ |  | \/ (/_ | |
#


@dataclass
class Hamiltonian_two_electrons_determinant_driven(Hamiltonian_two_electrons, object):
    d_two_e_integral: Two_electron_integral

    @staticmethod
    def H_ij_indices(
        det_i: Determinant, det_j: Determinant
    ) -> Iterator[Two_electron_integral_index_phase]:
        """General function to dispatch the evaluation of H_ij"""

        def H_ij_single_indices(
            sdet_i: Tuple[OrbitalIdx, ...],
            sdet_j: Tuple[OrbitalIdx, ...],
            sdet_k: Tuple[OrbitalIdx, ...],
            spin: str,
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly one orbital"""
            phase, h, p = det_i.single_exc(sdet_j, spin)

            for i in sdet_i:
                yield (h, i, p, i), phase
                yield (h, i, i, p), -phase
            for i in sdet_k:
                yield (h, i, p, i), phase

        def H_ij_doubleAA_indices(
            sdet_j: Tuple[OrbitalIdx, ...], spin
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly two orbitals within
            the same spin."""
            phase, h1, h2, p1, p2 = det_i.double_exc(sdet_j, spin)

            yield (h1, h2, p1, p2), phase
            yield (h1, h2, p2, p1), -phase

        def H_ij_doubleAB_2e_index(
            det_j: Determinant,
        ) -> Iterator[Two_electron_integral_index_phase]:
            """<I|H|J>, when I and J differ by exactly one alpha spin-orbital and
            one beta spin-orbital."""

            phaseA, h1, p1 = det_i.single_exc(det_j.alpha, "alpha")
            phaseB, h2, p2 = det_i.single_exc(det_j.beta, "beta")

            yield (h1, h2, p1, p2), phaseA * phaseB

        ed_up, ed_dn = det_i.exc_degree(det_j)
        # Same determinant -> Diagonal element
        if (ed_up, ed_dn) == (0, 0):
            yield from Hamiltonian_two_electrons_determinant_driven.H_ii_indices(det_i)
        # Single excitation
        elif (ed_up, ed_dn) == (1, 0):
            yield from H_ij_single_indices(det_i.alpha, det_j.alpha, det_i.beta, "alpha")
        elif (ed_up, ed_dn) == (0, 1):
            yield from H_ij_single_indices(det_i.beta, det_j.beta, det_i.alpha, "beta")
        # Double excitation of same spin
        elif (ed_up, ed_dn) == (2, 0):
            yield from H_ij_doubleAA_indices(det_j.alpha, "alpha")
        elif (ed_up, ed_dn) == (0, 2):
            yield from H_ij_doubleAA_indices(det_j.beta, "beta")
        # Double excitation of opposite spins
        elif (ed_up, ed_dn) == (1, 1):
            yield from H_ij_doubleAB_2e_index(det_j)

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
        # This is the function who will take foreever
        h = np.zeros(shape=(len(psi_internal), len(psi_external)))
        for (a, b), (i, j, k, l), phase in self.H_indices(psi_internal, psi_external):
            h[a, b] += phase * self.H_ijkl_orbital(i, j, k, l)
        return h


#   ___            _
#    |       _    |_ |  _   _ _|_ ._ _  ._   _
#    | \/\/ (_)   |_ | (/_ (_  |_ | (_) | | _>
#   ___                           _
#    |  ._ _|_  _   _  ._ _. |   | \ ._ o     _  ._
#   _|_ | | |_ (/_ (_| | (_| |   |_/ |  | \/ (/_ | |
#                   _|


@dataclass
class Hamiltonian_two_electrons_integral_driven(Hamiltonian_two_electrons, object):
    d_two_e_integral: Two_electron_integral

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

        det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
            spindet_occ, oppspindet_occ, d_occupied, "all"
        ) - Hamiltonian_two_electrons_integral_driven.get_dets_occ_in_orbitals(
            spindet_occ, oppspindet_occ, d_unoccupied, "any"
        )

        # if len(det_indices) == 0, `set()` is returned
        return det_indices

    @staticmethod
    def do_diagonal(
        det_indices: List[int], psi_i: Psi_det, det_to_index_j: Dict[Determinant, int], phase: int
    ):
        # contribution from integrals to diagonal elements
        for a in det_indices:
            # Handle PT2 case when psi_i != psi_j. In this case, psi_i[a] won't be in the external space and so error will be thrown
            if psi_i[a] in det_to_index_j:
                yield (
                    a,
                    det_to_index_j[psi_i[a]],
                ), phase  # Yield (a, J) v. (a, a) for MPI implementation
            else:
                pass

    @staticmethod
    def do_single(
        det_indices: List[int],
        phasemod: int,
        occ: OrbitalIdx,
        h: OrbitalIdx,
        p: OrbitalIdx,
        psi_internal: Psi_det,
        det_to_index: Dict[Determinant, int],
        spin: str,
    ):
        """Do all single excitations from hole h -> particle p; occ is index of orbital that is necessarily occupied
        Excitations from pre-filtered list of candidate |Determinant|s indicated by `det_indices`
        Called by category functions corresponding to single excitations

        For use in building the Hamiltonian in the variational step"""
        for I in det_indices:
            det = psi_internal[I]  # Grab |Determinant| I from w.f.
            if spin == "alpha":
                # Create new |Determinant| via excitation from h -> p
                # Hole, particle are alpha spin orbitals
                excited_det = det.apply_excitation(((h,), (p,)), ((), ()))
            else:  # Spin is "beta"
                # Hole, particle are beta spin orbitals
                excited_det = det.apply_excitation(((), ()), ((h,), (p,)))
            # If the excited determinant is in the internal wave function ->
            #   Compute phase of (single) excitation pair and yield (I, J), phase
            if excited_det in det_to_index:
                # :param `phasemod` is \pm 1, sign of two-electron integral in definition of SC-rules

                phase = phasemod * det.single_phase(h, p, spin)

                yield (I, det_to_index[excited_det]), phase
            else:
                pass

    @staticmethod
    def do_single_pt2(
        det_indices: List[int],
        phasemod: int,
        occ: OrbitalIdx,
        h: OrbitalIdx,
        p: OrbitalIdx,
        psi_internal: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spin: str,
    ):
        """Do all single excitations from hole h -> particle p; occ is index of orbital that is necessarily occupied
        Excitations from pre-filtered list of candidate |Determinant|s indicated by `det_indices`
        Called by category functions corresponding to single excitations

        For use in computing E_pt2 and subsequent selection"""
        for I in det_indices:
            det = psi_internal[I]  # Grab |Determinant| I from w.f.
            if spin == "alpha":
                # Create new |Determinant| via excitation from h -> p
                # Hole, particle are alpha spin orbitals
                excited_det = det.apply_excitation(((h,), (p,)), ((), ()))
            else:  # Spin is "beta"
                # Hole, particle are beta spin orbitals
                excited_det = det.apply_excitation(((), ()), ((h,), (p,)))
            # Assert the excited determinant satisfies the appropriate constraint C
            assert check_constraint(excited_det) == C
            # param `phasemod` is \pm 1, sign of two-electron integral in definition of SC-rules

            phase = phasemod * det.single_phase(h, p, spin)

            # excited_det is in the connected space by default; yield (I, det_J) phase
            # Cannot yield index of excited_det since this requires storing (knowing) connected space a priori
            yield (I, excited_det), phase

    @staticmethod
    def do_double_samespin(
        hp1: Tuple[OrbitalIdx, OrbitalIdx],
        hp2: Tuple[OrbitalIdx, OrbitalIdx],
        psi_internal: Psi_det,
        det_to_index: Dict[Determinant, int],
        spindet_occ_i: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ_i: Dict[OrbitalIdx, Set[int]],
        spin: str,
    ):
        """Do double excitations from i <-> j, k <-> l; hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        Electrons involved are of the same spin

        For use in building the Hamiltonian in the variational step"""
        # Unpack hole-particle pairs
        h1, p1 = hp1
        h2, p2 = hp2
        # Pre-filter; get list of candidate determinants thaat are possibly related via (same-spin) excitations h1 -> p1, h2 -> p2
        det_indices_AA = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
            spindet_occ_i, {}, {"same": {h1, h2}}, {"same": {p1, p1}}
        )
        for I in det_indices_AA:
            det = psi_internal[I]
            if spin == "alpha":
                # Create new |Determinant| via excitation from h1 -> p1, h2 -> p1
                excited_det = det.apply_excitation(((h1, h2), (p1, p2)), ((), ()))
            else:
                # Holes, particles are beta spin orbitals
                excited_det = det.apply_excitation(((), ()), ((h1, h2), (p1, p2)))
            # If the excited determinant is in the internal wave function ->
            #   Compute phase of (double) excitation pair and yield (I, J), phase
            if excited_det in det_to_index:
                phase = det.double_phase((h1, h2), (p1, p2), spin)
                if h2 < h1:
                    phase = -phase
                if p2 < p1:
                    phase = -phase

                yield (I, det_to_index[excited_det]), phase
            else:
                pass

    @staticmethod
    def do_double_samespin_pt2(
        hp1: Tuple[OrbitalIdx, OrbitalIdx],
        hp2: Tuple[OrbitalIdx, OrbitalIdx],
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_occ: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ: Dict[OrbitalIdx, Set[int]],
        spin: str,
        n_orb: int,
    ):
        """Do double excitations from i <-> j, k <-> l; hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        Electrons involved are of the same spin

        For use in computing E_pt2 and subsequent selection"""
        # Opposite-spin double excitations for category G
        a1 = min(C)  # `Lowest` constraint orbital
        # Unpack hole-particle pairs (both of input spin)
        h1, p1 = hp1
        h2, p2 = hp2
        if spin == "alpha":
            # Pre-processing; will this integral contribute to any (I, J) pairs s.to C?
            if (h1 in C) or (h2 in C):
                # Excitation pair will not satisfy C if either electron is excited out of C
                return None
            if ((p1 not in C) and (p1 > a1)) or (((p2 not in C) and (p2 > a1))):
                # Resulting excitation pair will satisfy `higher` constraint
                return None
            elif ((p1 not in C) and (p1 < a1)) and ((p2 not in C) and (p2 < a1)):
                # All excitation pairs related by <ij|kl> must already satisfy C
                # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h1, h2})) | {
                    p1,
                    p2,
                }
                # Related pairs must be:
                #   Occupied in: (alpha) h1, h2 C = {a1, a2, a3} (beta) none
                #   Empty in: (alpha) p1, p2 {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h1, h2} (beta) none
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        {},
                        {"same": ({h1, h2} | set(C))},
                        {"same": (unocc_spin_orbitals)},
                    )
                )
            elif (p1 not in C) and (p1 < a1):
                # p1 not in C, p2 is by above conditonals
                # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - ((set(C) - {p2}) | {h1, h2})) | {
                    p1,
                    p2,
                }
                # Related pairs must be:
                #   Occupied in: (alpha) h1, h2 C - {p2} (beta) none
                #   Empty in: (alpha) p1, p2 {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p2}) | {h1, h2}) (beta) none
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        {},
                        {"same": ({h1, h2} | (set(C) - {p2}))},
                        {"same": (unocc_spin_orbitals)},
                    )
                )
            elif (p2 not in C) and (p2 < a1):
                # p2 not in C, p1 is by above conditonals
                # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                unocc_spin_orbitals = (
                    set(range(a1 + 1, n_orb)) - ((set(C) - {p1, p2}) | {h1, h2})
                ) | {p1, p2}
                # Related pairs must be:
                #   Occupied in: (alpha) h1, h2 C - {p1} (beta) none
                #   Empty in: (alpha) p1, p2 {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p1}) | {h1, h2}) (beta) none
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        {},
                        {"same": ({h1, h2} | (set(C) - {p1}))},
                        {"same": (unocc_spin_orbitals)},
                    )
                )
            else:
                # Both p1, p2 in C
                unocc_spin_orbitals = (
                    set(range(a1 + 1, n_orb)) - ((set(C) - {p1, p2}) | {h1, h2})
                ) | {p1, p2}
                # Related pairs must be:
                #   Occupied in: (alpha) h1, h2 C - {p1, p2} (beta) none
                #   Empty in: (alpha) p1, p2 {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p1, p2}) | {h1, h2}) (beta) none
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        {},
                        {"same": ({h1, h2} | (set(C) - {p1, p2}))},
                        {"same": (unocc_spin_orbitals)},
                    )
                )
        else:  # Spin is beta
            # Here, candidates must alreaady be occupied in C
            unocc_oppspin_orbitals = set(range(a1 + 1, n_orb)) - set(C)
            # Related pairs must be:
            #   Occupied in: (alpha) C (beta) h1, h2
            #   Empty in: (alpha) {a1 + 1, a1 + 2, ... N_orb - 1} - C | {h1, h2}) (beta) p1, p2
            det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                spindet_occ,
                oppspindet_occ,
                {"same": {h1, h2}, "opposite": set(C)},
                {"same": {p1, p2}, "opposite": unocc_oppspin_orbitals},
            )

        # Now, loop through the filtered `candidate` determinants; generate the excitation pairs related by h1 -> p1, h2 -> p2
        for I in det_indices:
            det = psi[I]
            if spin == "alpha":
                # Create new |Determinant| via excitation from i -> j, k -> l
                excited_det = det.apply_excitation(((h1, h2), (p1, p2)), ((), ()))
            else:
                # Holes, particles are beta spin orbitals
                excited_det = det.apply_excitation(((), ()), ((h1, h2), (p1, p2)))
            # Assert the excited determinant satisfies the appropriate constraint C
            assert check_constraint(excited_det) == C
            phase = det.double_phase((h1, h2), (p1, p2), spin)
            if h2 < h1:
                phase = -phase
            if p2 < p1:
                phase = -phase
            yield (I, excited_det), phase

    @staticmethod
    def do_double_oppspin(
        hp1: Tuple[OrbitalIdx, OrbitalIdx],
        hp2: Tuple[OrbitalIdx, OrbitalIdx],
        psi_internal: Psi_det,
        det_to_index: Dict[Determinant, int],
        spindet_occ_i: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ_i: Dict[OrbitalIdx, Set[int]],
        spin: str,
    ):
        """Do double excitations from i <-> j, k <-> l; hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        Electrons involved are of the opposite-spin

        For use in building the Hamiltonian in the variational step"""
        # Unpack hole-particle pairs
        h1, p1 = hp1
        h2, p2 = hp2
        # Pre-filter; get list of candidate determinants thaat are possibly related via (opposite-spin) excitations h1 -> p1, h2 -> p2
        det_indices_AB = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
            spindet_occ_i,
            oppspindet_occ_i,
            {"same": {h1}, "opposite": {h2}},
            {"same": {p1}, "opposite": {p2}},
        )
        for I in det_indices_AB:
            det = psi_internal[I]
            if spin == "alpha":
                # h1, p1 -> alpha spin-orbitals, h2, p2 -> beta
                excited_det = det.apply_excitation(((h1,), (p1,)), ((h2,), (p2,)))
                # Phase is computed from both spindets
                phaseA = det.single_phase(h1, p1, spin)
                phaseB = det.single_phase(h2, p2, "beta")
            else:
                # h1, p1 -> beta spin-orbitals, h2, p2 -> alpha
                excited_det = det.apply_excitation(((h2,), (p2,)), ((h1,), (p1,)))
                phaseA = det.single_phase(h1, p1, spin)
                phaseB = det.single_phase(h2, p2, "alpha")
            # If the excited determinant is in the internal wave function ->
            #   Compute phase of (double) excitation pair and yield (I, J), phase
            if excited_det in det_to_index:
                yield (I, det_to_index[excited_det]), phaseA * phaseB
            else:
                pass

    @staticmethod
    def do_double_oppspin_pt2(
        hp1: Tuple[OrbitalIdx, OrbitalIdx],
        hp2: Tuple[OrbitalIdx, OrbitalIdx],
        psi: Determinant,
        C: Tuple[OrbitalIdx, ...],
        spindet_occ: Dict[OrbitalIdx, Set[int]],
        oppspindet_occ: Dict[OrbitalIdx, Set[int]],
        spin: str,
        n_orb: int,
    ):
        """Do double excitations from i <-> j, k <-> l; hp1 = i, j or j, i, hp2 = k, l or l, k, particle-hole pairs
        Electrons involved are of the opposite-spin

        For use in computing E_pt2 energy and subsequent selection"""
        # Opposite-spin double excitations for category G only
        a1 = min(C)  # `Lowest` constraint orbital
        # Unpack hole-particle pairs
        h1, p1 = hp1  # This excitation is of input spin (e.g., alpha)
        h2, p2 = hp2  # This excitation is of oppsoite spin (e.g., beta)
        # Pre-processing; will this integral contribute to any (I, J) pairs s.to C?
        if spin == "alpha":
            if h1 in C:
                # Excitation pair will not satisfy C if either electron is excited out of C
                return None
            if (p1 not in C) and (p1 > a1):
                # Resulting excitation pair will satisfy `higher` constraint
                return None
            elif (p1 not in C) and (p1 < a1):
                # All excitation pairs related by <ij|kl> must already satisfy C
                # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h1})) | {p1}
                # Related pairs must be:
                #   Occupied in: (alpha) h1, C = {a1, a2, a3} (beta) h2
                #   Empty in: (alpha) p1, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h1} (beta) p2
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        oppspindet_occ,
                        {"same": ({h1} | set(C)), "opposite": {h2}},
                        {"same": (unocc_spin_orbitals), "opposite": {p2}},
                    )
                )
            else:
                # By above -> p1 \in C in this instance
                # All excitation pairs related by <ij|kl> must be occupied in C - {p1}
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) - {p1} | {h1})) | {p1}
                # Related pairs must be:
                #   Occupied in: (alpha) h1, C - {p1} (beta) h2
                #   Empty in: (alpha) p1, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p1}) | {h1}) (beta) p2
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        oppspindet_occ,
                        {"same": ({h1} | (set(C) - {p1})), "opposite": {h2}},
                        {"same": unocc_spin_orbitals, "opposite": {p2}},
                    )
                )
        else:  # spin is beta
            if h2 in C:
                # Excitation pair will not satisfy C if either electron is excited out of C
                return None
            if (p2 not in C) and (p2 > a1):
                # Resulting excitation pair will satisfy `higher` constraint
                return None
            elif (p2 not in C) and (p2 < a1):
                # All excitation pairs related by <ij|kl> must already satisfy C
                # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h2})) | {p2}
                # Related pairs must be:
                #   Occupied in: (alpha) h2, C = {a1, a2, a3} (beta) h1
                #   Empty in: (alpha) p2, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h2} (beta) p1
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        oppspindet_occ,
                        {"same": {h1}, "opposite": ({h2} | set(C))},
                        {"same": {p1}, "opposite": unocc_spin_orbitals},
                    )
                )
            else:
                # By above -> p2 \in C in this instance
                # All excitation pairs related by <ij|kl> must be occupied in C - {p2}
                unocc_spin_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) - {p2} | {h2})) | {p2}
                # Related pairs must be:
                #   Occupied in: (alpha) h2, C - {p2} (beta) h1
                #   Empty in: (alpha) p2, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p2}) | {h2}) (beta) p1
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        oppspindet_occ,
                        {"same": {h1}, "opposite": ({h2} | (set(C) - {p2}))},
                        {"same": {p1}, "opposite": unocc_spin_orbitals},
                    )
                )
        # Now, loop through filtered dets to yield excitation pairs s.to C
        for I in det_indices:
            det = psi[I]
            if spin == "alpha":
                # h1, p1 -> alpha spin-orbitals, h2, p2 -> beta
                excited_det = det.apply_excitation(((h1,), (p1,)), ((h2,), (p2,)))
                # Phase is computed from both spindets
                phaseA = det.single_phase(h1, p1, spin)
                phaseB = det.single_phase(h2, p2, "beta")
            else:
                # h1, p1 -> beta spin-orbitals, h2, p2 -> alpha
                excited_det = det.apply_excitation(((h2,), (p2,)), ((h1,), (p1,)))
                phaseA = det.single_phase(h1, p1, spin)
                phaseB = det.single_phase(h2, p2, "alpha")
            # Assert excited det satisfies constraint and yield
            assert check_constraint(excited_det) == C
            yield (I, excited_det), phaseA * phaseB

    @staticmethod
    def category_A(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category A. Used in the Hamiltonian build
        Category A possibilties:
            i = k = j = l: e.g., (1, 1, 1, 1)
        Contributes only to diagonals. Necessarily, opposite spin occupied only.

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category A, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "A"

        def do_diagonal_A(i, j, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i):
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
    def category_B(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category B. Used in the Hamiltonian build
        Category B possibilties:
            i = k < j = l: e.g., (1, 2, 1, 2)
        Contributes only to diagonals. Same + opposite spin occ.

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category B, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
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
    def category_C(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j,
        spindet_a_occ_i,
        spindet_b_occ_i,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category C. Used in the Hamiltonian build
        Category C possibilties:
            i = k < j < l: e.g., (1, 2, 1, 3)
            i < k < j = l: e.g., (1, 3, 2, 3)
            j < i = k < l: e.g., (2, 1, 2, 3)
        Contributes only to singles (where occ is same spin or opposite spin).

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category C, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "C"

        def do_single_C(i, j, k, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin):
            # One way: Indices of determinants related by excitations from psi_i -> psi_j
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
                det_indices_1, 1, j, i, k, psi_i, det_to_index_j, spin
            )
            # Other way: Indices of determinants related by excitations from psi_j -> psi_i
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
                det_indices_2, 1, j, k, i, psi_i, det_to_index_j, spin
            )

        if i == k:  # <ij|il> = <ji|li>, ja(b) <-> la(b), occ = ia or ib
            yield from do_single_C(
                j,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
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
            )
        else:  # j == l, <ji|jk> = <ij|kj>, ia(b) to ka(b), occ = ja or jb
            yield from do_single_C(
                i,
                j,
                k,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
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
            )

    @staticmethod
    def category_C_pt2(
        idx: Two_electron_integral_index,
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ: Dict[OrbitalIdx, Set[int]],
        n_orb: int,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category C, s.to J \in constraint for use in PT2 selection
        Category C possibilties:
            i = k < j < l: e.g., (1, 2, 1, 3)
            i < k < j = l: e.g., (1, 3, 2, 3)
            j < i = k < l: e.g., (2, 1, 2, 3)
        Contributes only to singles (where occ is same spin or opposite spin).

        Inputs:
        :param idx:                          (i, j, k, l) index of two-electron integral
        :param psi:                          List of internal determinants (wave function)
        :param C:                            Constraint as |Spin_determinant|, three `highest` occupied alpha spin orbitals
        :param spindet_a_occ, spindet_b_occ: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category C, return determinant pairs (I, J) \in (psi, psi_connected) and associated phase s.to J satisfies C
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "C"

        def do_single_C_pt2(occ, h, p, psi, C, spindet_occ, oppspindet_occ, spin, n_orb):
            # Phasemod is always +1 in category C
            a1 = min(C)  # `Lowest` constraint orbital
            if spin == "alpha":  # If p -> h excitation is alpha spin
                # Pre-processing; will this integral contribute to any (I, J) pairs s.to C?
                if h in C:
                    # Excitation pair will not satisfy C if electron is excited out of C
                    return None
                if (p not in C) and (p > a1):
                    # Resulting excitation pair will satisfy `higher` constraint
                    return None
                elif (p not in C) and (p < a1):
                    # All excitation pairs related by <ij|kl> must already satisfy C
                    # More cases, depending on which orbital occ is
                    if (occ not in C) & (occ > a1):
                        # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                        # So, in this case only yield related pairs where the occ orbital is beta spin
                        # Get unocc orbitals not in C (including `higher` ones) -> must be empty in the excitation pairs to satisfy C
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h, C = {a1, a2, a3} (beta) occ
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h} (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": ({h} | set(C)), "opposite": {occ}},
                            {"same": unocc_orbitals},
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, 1, occ, h, p, psi, C, spin
                        )
                    else:
                        # Here, occ is either \in C, or \not\in C and < a1
                        # Now, can yield related pairs where occ is alpha or beta spin (alpha case won't affect C)
                        # Get unocc orbitals not in C (including `higher` ones) -> must be empty in the excitation pairs to satisfy C
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h, C = {a1, a2, a3} (beta) occ, or (alpha) h, C = {a1, a2, a3}, occ (beta) none,
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h} (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = chain(
                            Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                                spindet_occ,
                                oppspindet_occ,
                                {"same": ({h} | set(C)), "opposite": {occ}},
                                {"same": unocc_orbitals},
                            ),
                            Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                                spindet_occ,
                                {},
                                {"same": ({occ, h} | set(C))},
                                {"same": unocc_orbitals},
                            ),
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, 1, occ, h, p, psi, C, spin
                        )
                else:
                    # By above -> p \in C in this instance
                    # All excitation pairs related by <ij|kl> must be occupied in C - {p}
                    if (occ not in set(C)) & (occ > a1):
                        # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                        # So, in this case only yield related pairs where the occ orbital is beta spin
                        # Get unocc orbitals not in C (including `higher` ones) -> must be empty in the excitation pairs to satisfy C
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - ((set(C) - {p}) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h, C - {p} (beta) occ
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p}) | {h}) (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": ({h} | (set(C) - {p})), "opposite": {occ}},
                            {"same": unocc_orbitals},
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, 1, occ, h, p, psi, C, spin
                        )
                    else:
                        # Here, occ is either \in C, or \not\in C and < a1
                        # Now, can yield related pairs where occ is alpha or beta spin (alpha case won't affect C)
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - ((set(C) - {p}) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h, C - {p}  (beta) occ, or (alpha) h,  C - {p}, occ (beta) none,
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p}) | {h}) (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = chain(
                            Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                                spindet_occ,
                                oppspindet_occ,
                                {"same": ({h} | (set(C) - {p})), "opposite": {occ}},
                                {"same": unocc_orbitals},
                            ),
                            Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                                spindet_occ,
                                {},
                                {"same": ({occ, h} | (set(C) - {p}))},
                                {"same": unocc_orbitals},
                            ),
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, 1, occ, h, p, psi, C, spin
                        )
            else:  # spin == "beta"
                # All excitation pairs related by <ij|kl> must already satisfy C
                if (occ not in set(C)) & (occ > a1):
                    # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                    # So, in this case only yield related pairs where the occ orbital is beta spin
                    # Get `higher` orbitals not in C -> must be empty in the excitation pairs to satisfy C
                    det_indices = (
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": {h, occ}, "opposite": set(C)},
                            {
                                "same": {p},
                                "opposite": (set(range(a1 + 1, n_orb)) - set(C)),
                            },
                        )
                    )
                    yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                        det_indices, 1, occ, h, p, psi, C, spin
                    )
                else:  # Both cases apply here (occ can be alpha spin)
                    # Occ is necessarily either in C or < a1, so don't demand its unoccupied
                    det_indices = chain(
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": {h, occ}, "opposite": set(C)},
                            {
                                "same": {p},
                                "opposite": (set(range(a1 + 1, n_orb)) - set(C)),
                            },
                        ),
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": {h}, "opposite": (set(C) | {occ})},
                            {
                                "same": {p},
                                "opposite": (set(range(a1 + 1, n_orb)) - (set(C) | {occ})),
                            },
                        ),
                    )
                    yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                        det_indices, 1, occ, h, p, psi, C, spin
                    )

        if i == k:  # <ij|il> = <ji|li>, ja(b) <-> la(b), occ = ia or ib
            yield from do_single_C_pt2(
                i, j, l, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_C_pt2(
                i, l, j, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_C_pt2(i, j, l, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_C_pt2(i, l, j, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)

        else:  # j == l, <ji|jk> = <ij|kj>, ia(b) to ka(b), occ = ja or jb
            yield from do_single_C_pt2(
                j, i, k, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_C_pt2(
                j, k, i, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_C_pt2(j, i, k, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_C_pt2(j, k, i, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)

    @staticmethod
    def category_D(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category D. For use in the Hamiltonian build
        Category D possibilties:
            i = j = k < l: e.g., (1, 1, 1, 2)
            i < j = k = l: e.g., (1, 2, 2, 2)
        Necessarily, only opposite spin excitations are allowed (e.g., occ = 1a, 1b <-> 2b)

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category D, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "D"

        def do_single_D(i, j, l, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin):
            # One way: Indices of determinants related by excitations from psi_i -> psi_j
            # phasemod, occ, h, p = 1, i, j, l
            det_indices_1 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {j}, "opposite": {i}}, {"same": {l}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_1, 1, i, j, l, psi_i, det_to_index_j, spin
            )
            # Other way: Indices of determinants related by excitations from psi_j -> psi_i
            # phasemod, occ, h, p = 1, i, l, j
            det_indices_2 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {l}, "opposite": {i}}, {"same": {j}}
                )
            )

            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_2, 1, i, l, j, psi_i, det_to_index_j, spin
            )

        if i == j:  # <ii|il>, ia(b) <-> la(b), occ = ib(a)
            yield from do_single_D(
                i,
                i,
                l,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
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
            )
        else:  # i < j == k == l, <ij|jj> = <jj|ij> = <jj|ji>, ja(b) <-> ia(b) occ = jb(a)
            yield from do_single_D(
                j,
                j,
                i,
                psi_i,
                det_to_index_j,
                spindet_a_occ_i,
                spindet_b_occ_i,
                "alpha",
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
            )

    @staticmethod
    def category_D_pt2(
        idx: Two_electron_integral_index,
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ: Dict[OrbitalIdx, Set[int]],
        n_orb,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category D, s.to J \in constraint for use in PT2 selection
        Category D possibilties:
            i = j = k < l: e.g., (1, 1, 1, 2)
            i < j = k = l: e.g., (1, 2, 2, 2)
        Necessarily, only opposite spin excitations are allowed (e.g., occ = 1a, 1b <-> 2b)

        Inputs:
        :param idx:                          (i, j, k, l) index of two-electron integral
        :param psi:                          List of internal determinants (wave function)
        :param C:                            Constraint as |Spin_determinant|, three `highest` occupied alpha spin orbitals
        :param spindet_a_occ, spindet_b_occ: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category D, return determinant pairs (I, J) \in (psi, psi_connected) and associated phase s.to J satisfies C
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "D"

        def do_single_D_pt2(occ, h, p, psi, C, spindet_occ, oppspindet_occ, spin, n_orb):
            # TODO: Re-factor s.t. static part and part dep on psi are separate
            # Phasemod is always +1 in category D
            # Only opposite-spin single excitations are allowed
            a1 = min(C)  # `Lowest` constraint orbital
            if spin == "alpha":  # If p -> h excitation is alpha spin
                # Pre-processing; will this integral contribute to any (I, J) pairs s.to C?
                if h in C:
                    # Excitation pair will not satisfy C if electron is excited out of C
                    return None
                if (p not in C) and (p > a1):
                    # Resulting excitation pair will satisfy `higher` constraint
                    return None
                elif (p not in C) and (p < a1):
                    # All excitation pairs related by <ij|kl> must already satisfy C
                    # Since we are in category D, we need only do the case when occ is opposite spin
                    # Here, excitation is alpha -> occ is beta, no restrictions based on occ
                    unocc_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h})) | {p}
                    # Related pairs must be:
                    #   Occupied in: (alpha) h, C = {a1, a2, a3} (beta) occ
                    #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h} (beta) none
                    # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                    det_indices = (
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": ({h} | set(C)), "opposite": {occ}},
                            {"same": unocc_orbitals},
                        )
                    )
                    yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                        det_indices, 1, occ, h, p, psi, C, spin
                    )
                else:
                    # By above -> p \in C in this instance
                    # All excitation pairs related by <ij|kl> must be occupied in C - {p}
                    # Since we are in category D, we need only do the case when occ is opposite spin
                    # Here, excitation is alpha -> occ is beta, no restrictions based on occ
                    unocc_orbitals = (set(range(a1 + 1, n_orb)) - ((set(C) - {p}) | {h})) | {p}
                    # Related pairs must be:
                    #   Occupied in: (alpha) h, C - {p} (beta) occ
                    #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p}) | {h}) (beta) none
                    # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                    det_indices = (
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": ({h} | (set(C) - {p})), "opposite": {occ}},
                            {"same": unocc_orbitals},
                        )
                    )
                    yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                        det_indices, 1, occ, h, p, psi, C, spin
                    )
            else:  # spin == "beta"
                # All excitation pairs related by <ij|kl> must already satisfy C
                # Now, occ is necessarily an alpha orbital, have some restrictions based on it
                if (occ not in set(C)) & (occ > a1):
                    # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                    # Normally, would only yield pairs where occ orbitals is beta spin. But this is not possible for category D, so we pass
                    return None
                else:
                    # Occ is necessarily either in C or < a1, so don't demand its unoccupied
                    unocc_orbitals = set(range(a1 + 1, n_orb)) - (set(C) | {occ})
                    det_indices = (
                        Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            oppspindet_occ,
                            {"same": {h}, "opposite": (set(C) | {occ})},
                            {
                                "same": {p},
                                "opposite": unocc_orbitals,
                            },
                        )
                    )
                    yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                        det_indices, 1, occ, h, p, psi, C, spin
                    )

        if i == j:  # <ii|il>, ia(b) <-> la(b), occ = ib(a)
            yield from do_single_D_pt2(
                i, i, l, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_D_pt2(
                i, l, i, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_D_pt2(i, i, l, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_D_pt2(i, l, i, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
        else:  # i < j == k == l, <ij|jj> = <jj|ij> = <jj|ji>, ja(b) <-> ia(b) occ = jb(a)
            yield from do_single_D_pt2(
                j, j, i, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_D_pt2(
                j, i, j, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_D_pt2(j, j, i, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_D_pt2(j, i, j, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)

    @staticmethod
    def category_E(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category E. For use in the Hamiltonian build
        Category E possibilties:
            i = j < k < l: e.g., (1, 1, 2, 3)
            i < j = k < l: e.g., (1, 2, 2, 3)
            i < j < k = l: e.g., (1, 2, 3, 3)
        This category contributes to single (where occ is same-spin, necessarily) and double (opposite-spin) excitation pairs

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category E, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "E"

        def do_single_E(i, k, l, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i, spin):
            # One way: Indices of determinants related by excitations from psi_i -> psi_j
            # phasemod, occ, h, p = -1, i, k, l
            det_indices_1 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, k}}, {"same": {l}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_1, -1, i, k, l, psi_i, det_to_index_j, spin
            )
            # Other way: Indices of determinants related by excitations from psi_j -> psi_i
            # phasemod, occ, h, p = -1, i, l, k
            det_indices_2 = (
                Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                    spindet_occ_i, oppspindet_occ_i, {"same": {i, l}}, {"same": {k}}
                )
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_single(
                det_indices_2, -1, i, l, k, psi_i, det_to_index_j, spin
            )

        # doubles, ia(b) to ka(b) and jb(a) to lb(a)
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta"
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
            )

    @staticmethod
    def category_E_pt2(
        idx: Two_electron_integral_index,
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ: Dict[OrbitalIdx, Set[int]],
        n_orb,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category E, s.to J \in constraint for use in PT2 selection
        Category E possibilties:
            i = j < k < l: e.g., (1, 1, 2, 3)
            i < j = k < l: e.g., (1, 2, 2, 3)
            i < j < k = l: e.g., (1, 2, 3, 3)
        This category contributes to single (where occ is same-spin, necessarily) and double (opposite-spin) excitation pairs

        Inputs:
        :param idx:                          (i, j, k, l) index of two-electron integral
        :param psi:                          List of internal determinants (wave function)
        :param C:                            Constraint as |Spin_determinant|, three `highest` occupied alpha spin orbitals
        :param spindet_a_occ, spindet_b_occ: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category E, return determinant pairs (I, J) \in (psi, psi_connected) and associated phase s.to J satisfies C
        """

        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "E"

        def do_single_E_pt2(occ, h, p, psi, C, spindet_occ, oppspindet_occ, spin, n_orb):
            # Phasemod is always -1 in category E
            # Only same-spin single excitations are allowed
            a1 = min(C)  # `Lowest` constraint orbital
            if spin == "alpha":  # If p -> h excitation is alpha spin
                # Pre-processing; will this integral contribute to any (I, J) pairs s.to C?
                if h in C:
                    # Excitation pair will not satisfy C if electron is excited out of C
                    return None
                if (p not in C) and (p > a1):
                    # Resulting excitation pair will satisfy `higher` constraint
                    return None
                if (p not in C) and (p < a1):
                    # All excitation pairs related by <ij|kl> must already satisfy C
                    # Since we are in category E, we need only do the case when occ is same spin as (h, p) pair
                    # Here, excitation is alpha -> occ is alpha, further restrictions required
                    if (occ not in C) & (occ > a1):
                        # TODO: Flatten this with above if
                        # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                        # Normally, would only yield pairs where occ orbitals is beta spin. But this is not possible for category E, so we pass
                        return None
                    else:
                        # Here, occ is either \in C, or \not\in C and < a1
                        # Now, can yield related pairs where occ is alpha spin
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - (set(C) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h, C = {a1, a2, a3}, occ (beta) none,
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - {a1, a2, a3, h} (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            {},
                            {"same": ({occ, h} | set(C))},
                            {"same": unocc_orbitals},
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, -1, occ, h, p, psi, C, spin
                        )
                else:
                    # By above -> p \in C in this instance
                    # All excitation pairs related by <ij|kl> must be occupied in C - {p}
                    if (occ not in set(C)) & (occ > a1):
                        # If occ (alpha) is \not\in C and > a1 -> Excitation pairs related by <ij|kl> necessarily satisfy a different constraint
                        # Normally, would only yield pairs where occ orbitals is beta spin. But this is not possible for category E, so we pass
                        return None
                    else:
                        # Here, occ is either \in C, or \not\in C and < a1
                        # Now, can yield related pairs where occ is alpha
                        unocc_orbitals = (set(range(a1 + 1, n_orb)) - ((set(C) - {p}) | {h})) | {p}
                        # Related pairs must be:
                        #   Occupied in: (alpha) h,  C - {p}, occ (beta) none,
                        #   Empty in: (alpha) p, {a1 + 1, a1 + 2, ... N_orb - 1} - ((C - {p}) | {h}) (beta) none
                        # p \not\in C in this instance, and < a1, so must include in `empty` orbital set
                        det_indices = Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                            spindet_occ,
                            {},
                            {"same": ({occ, h} | (set(C) - {p}))},
                            {"same": unocc_orbitals},
                        )
                        yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                            det_indices, -1, occ, h, p, psi, C, spin
                        )
            else:  # spin == "beta"
                # All excitation pairs related by <ij|kl> must already satisfy C
                # Necessarily, integrals in this category only invoke same-spin single excitations
                # So, in this instance, occ is beta spin and has no restrictions on it
                det_indices = (
                    Hamiltonian_two_electrons_integral_driven.get_dets_via_orbital_occupancy(
                        spindet_occ,
                        oppspindet_occ,
                        {"same": {h, occ}, "opposite": set(C)},
                        {
                            "same": {p},
                            "opposite": (set(range(a1 + 1, n_orb)) - set(C)),
                        },
                    )
                )
                yield from Hamiltonian_two_electrons_integral_driven.do_single_pt2(
                    det_indices, -1, occ, h, p, psi, C, spin
                )

        # doubles, ia(b) to ka(b) and jb(a) to lb(a)
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
                hp1, hp2, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
                hp1, hp2, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb
            )

        if i == j:  # <ii|kl> = <ii|lk> = <ik|li> -> - <ik|il>
            # singles, ka(b) <-> la(b), occ = ia(b)
            yield from do_single_E_pt2(
                i, k, l, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(
                i, l, k, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(i, k, l, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_E_pt2(i, l, k, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
        elif j == k:  # <ij|jl> = - <ij|lj>
            # singles, ia(b) <-> la(b), occ = ja(b)
            yield from do_single_E_pt2(
                j, i, l, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(
                j, l, i, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(j, i, l, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_E_pt2(j, l, i, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
        else:  # k == l, <ij|kk> = <ji|kk> = <jk|ki> -> -<jk|ik>
            # singles, ja(b) <-> ia(b) occ = ka(b)
            yield from do_single_E_pt2(
                k, i, j, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(
                k, j, i, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from do_single_E_pt2(k, i, j, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)
            yield from do_single_E_pt2(k, j, i, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb)

    @staticmethod
    def category_F(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category F. For use in the Hamiltonian build
        Category F possibilties:
            i = j < k = l: e.g., (1, 1, 2, 2)
        This category contributes to diagonals (same-spin) and double (opposite-spin) excitation pairs

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category F, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "F"

        def do_diagonal_F(i, k, psi_i, det_to_index_j, spindet_occ_i, oppspindet_occ_i):
            # Should have negative phase, since <11|22> = <12|21> -> <12|12> with negative factor
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
            [i, k], [i, k], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
        )
        # Need to do ph1, ph2 pairing twice, once for each spin. ia -> ka, kb -> ib
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [i, k], [k, i], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
        )
        # Double from ia -> ka, kb -> ib
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [i, k], [k, i], psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta"
        )
        # Only call for a single spin variable. Each excitation involves ia, ib to ka, kb. Flipping the spin just double counts it
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
            [k, i], [k, i], psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
        )

    @staticmethod
    def category_F_pt2(
        idx: Two_electron_integral_index,
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ: Dict[OrbitalIdx, Set[int]],
        n_orb,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category F, s.to J \in constraint for use in PT2 selection
        Category F possibilties:
            i = j < k = l: e.g., (1, 1, 2, 2)
        This category contributes to diagonals (not relevant for PT2) and double (opposite-spin) excitation pairs

        Inputs:
        :param idx:                          (i, j, k, l) index of two-electron integral
        :param psi:                          List of internal determinants (wave function)
        :param C:                            Constraint as |Spin_determinant|, three `highest` occupied alpha spin orbitals
        :param spindet_a_occ, spindet_b_occ: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category F, return determinant pairs (I, J) \in (psi, psi_connected) and associated phase s.to J satisfies C
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "F"

        # Only call for a single spin variable. Each excitation involves ia, ib to ka, kb. Flipping the spin just double counts it
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
            [i, k], [i, k], psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
        )
        # Need to do ph1, ph2 pairing twice, once for each spin. ia -> ka, kb -> ib
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
            [i, k], [k, i], psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
        )
        # Double from ia -> ka, kb -> ib
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
            [i, k], [k, i], psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb
        )
        # Only call for a single spin variable. Each excitation involves ia, ib to ka, kb. Flipping the spin just double counts it
        yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
            [k, i], [k, i], psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
        )

    @staticmethod
    def category_G(
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[Determinant, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category G. For use in the Hamiltonian build
        Category G possibilties:
            i < j < k < l: e.g., (1, 2, 3, 4)
            i < k < j < l: e.g., (1, 3, 2, 4)
            j < i < k < l: e.g., (2, 1, 3, 4)
        This category contributes to opposite-spin and same-spin double excitations

        Inputs:
        :param idx:                              (i, j, k, l) index of two-electron integral
        :param psi_i:                            List of internal determinants (wave function)
        :param det_to_index_j:                   Hash map of determinants -> Associated indices in psi_j
        :param spindet_a_occ_i, spindet_b_occ_i: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category G, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase
        """
        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "G"

        # doubles, i to k and j to l, same spin and opposite-spin excitations allowed
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta"
            )
        # doubles, i to k and j to l, same spin and opposite-spin excitations allowed
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i, "alpha"
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin(
                hp1, hp2, psi_i, det_to_index_j, spindet_b_occ_i, spindet_a_occ_i, "beta"
            )

    @staticmethod
    def category_G_pt2(
        idx: Two_electron_integral_index,
        psi: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ: Dict[OrbitalIdx, Set[int]],
        n_orb,
    ):
        """
        Return determinant pairs (I, J) connected by integral idx in category G, s.to J \in constraint for use in PT2 selection
        Category G possibilties:
            i < j < k < l: e.g., (1, 2, 3, 4)
            i < k < j < l: e.g., (1, 3, 2, 4)
            j < i < k < l: e.g., (2, 1, 3, 4)
        This category contributes to opposite-spin and same-spin double excitations

        Inputs:
        :param idx:                          (i, j, k, l) index of two-electron integral
        :param psi:                          List of internal determinants (wave function)
        :param C:                            Constraint as |Spin_determinant|, three `highest` occupied alpha spin orbitals
        :param spindet_a_occ, spindet_b_occ: Dictionaries mapping |OrbitalIdx| -> Indices of determinants occupied in associated orbital

        Outputs:
        For two-electron integral (i, j, k, l) in category G, return determinant pairs (I, J) \in (psi_i, psi_j) and associated phase s.to J satisfies C
        """

        i, j, k, l = idx
        assert integral_category(i, j, k, l) == "G"

        # Doubles (same-spin) i <-> k and j <-> l
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin_pt2(
                hp1, hp2, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_samespin_pt2(
                hp1, hp2, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb
            )
        # Doubles (opposite-spin) i <-> k and j <-> l
        for hp1, hp2 in product(permutations([i, k], 2), permutations([j, l], 2)):
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
                hp1, hp2, psi, C, spindet_a_occ, spindet_b_occ, "alpha", n_orb
            )
            yield from Hamiltonian_two_electrons_integral_driven.do_double_oppspin_pt2(
                hp1, hp2, psi, C, spindet_b_occ, spindet_a_occ, "beta", n_orb
            )

    def H_indices(
        self, psi_i: Psi_det, psi_j: Psi_det
    ) -> Iterator[Two_electron_integral_index_phase]:
        # Returns H_indices, and idx of associated integral
        generator = H_indices_generator(psi_i, psi_j)
        spindet_a_occ_i, spindet_b_occ_i = generator.spindet_occ_int
        det_to_index_j = generator.det_to_index
        for idx4, _ in self.d_two_e_integral.items():
            idx = compound_idx4_reverse(idx4)
            for (
                (a, b),
                phase,
            ) in self.H_indices_idx(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i):
                yield (a, b), idx, phase

    def H_indices_idx(
        self,
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        det_to_index_j: Dict[OrbitalIdx, int],
        spindet_a_occ_i: Dict[OrbitalIdx, Set[int]],
        spindet_b_occ_i: Dict[OrbitalIdx, Set[int]],
    ) -> Iterator[Two_electron_integral_index_phase]:
        # Call to get indices of determinant pairs + associated phase for a given integral idx
        category = integral_category(*idx)
        if category == "A":
            yield from self.category_A(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "B":
            yield from self.category_B(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "C":
            yield from self.category_C(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "D":
            yield from self.category_D(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "E":
            yield from self.category_E(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "F":
            yield from self.category_F(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)
        if category == "G":
            yield from self.category_G(idx, psi_i, det_to_index_j, spindet_a_occ_i, spindet_b_occ_i)

    def H_indices_pt2(
        self, psi_i: Psi_det, C: Tuple[OrbitalIdx, ...]
    ) -> Iterator[Two_electron_integral_index_phase]:
        # Returns H_indices, and idx of associated integral
        # For pt2 selection!
        generator = H_indices_generator(psi_i)
        spindet_a_occ_i, spindet_b_occ_i = generator.spindet_occ_int
        for idx4, _ in self.d_two_e_integral.items():
            idx = compound_idx4_reverse(idx4)
            for (
                (I, det_J),
                phase,
            ) in self.H_indices_idx_pt2(idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i):
                yield (I, det_J), idx, phase

    def H_indices_idx_pt2(
        self,
        idx: Two_electron_integral_index,
        psi_i: Psi_det,
        C: Tuple[OrbitalIdx, ...],
        spindet_a_occ_i,
        spindet_b_occ_i,
    ) -> Iterator[Two_electron_integral_index_phase]:
        # Call to get indices of determinant pairs + associated phase for a given integral idx
        category = integral_category(*idx)
        if category == "A":
            pass
        if category == "B":
            pass
        if category == "C":
            yield from self.category_C_pt2(
                idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "D":
            yield from self.category_D_pt2(
                idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "E":
            yield from self.category_E_pt2(
                idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "F":
            yield from self.category_F_pt2(
                idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )
        if category == "G":
            yield from self.category_G_pt2(
                idx, psi_i, C, spindet_a_occ_i, spindet_b_occ_i, self.N_orb
            )

    def H(self, psi_i, psi_j) -> List[List[Energy]]:
        generator = H_indices_generator(psi_i, psi_j)
        spindet_a_occ_i, spindet_b_occ_i = generator.spindet_occ_int
        det_to_index_j = generator.det_to_index
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


class H_indices_generator(object):
    """Generate and cache necessary utilities for building the
    two-electron Hamiltonian in an integral-driven fashion.
    Re-created at each CIPSI iteration; i.e. for each new list of internal determinants."""

    def __init__(self, psi_internal: Psi_det, psi_external: Psi_det = None):
        # Application dependent
        # If Davidson diagonalization, psi_i = psi_j
        # If PT2 selection, psi_i \neq psi_j
        if psi_external is None:
            psi_external = psi_internal
        self.psi_i = psi_internal
        self.psi_j = psi_external

    @staticmethod
    def get_spindet_a_occ_spindet_b_occ(
        psi_i: Psi_det,
    ) -> Tuple[Dict[OrbitalIdx, Set[int]], Dict[OrbitalIdx, Set[int]]]:
        """
        Return (two) dicts mapping spin orbital indices -> determinants that are occupied in those orbitals
        >>> H_indices_generator.get_spindet_a_occ_spindet_b_occ([Determinant(alpha=(0,1),beta=(1,2)),Determinant(alpha=(1,3),beta=(4,5))])
        (defaultdict(<class 'set'>, {0: {0}, 1: {0, 1}, 3: {1}}),
         defaultdict(<class 'set'>, {1: {0}, 2: {0}, 4: {1}, 5: {1}}))
        >>> H_indices_generator.get_spindet_a_occ_spindet_b_occ([Determinant(alpha=(0,),beta=(0,))])[0][1]
        set()
        """

        # TODO: Implement bitstring rep
        # Can generate det_to_indices hash in here
        def get_dets_occ(psi_i: Psi_det, spin: str) -> Dict[OrbitalIdx, Set[int]]:
            ds = defaultdict(set)
            for i, det in enumerate(psi_i):
                for o in getattr(det, spin):
                    ds[o].add(i)
            return ds

        return tuple(get_dets_occ(psi_i, spin) for spin in ["alpha", "beta"])

    @cached_property
    def det_to_index(self):
        # Create and cache dictionary mapping connected determinants \in psi_j to associated indices.
        return {det: i for i, det in enumerate(self.psi_j)}

    @cached_property
    def spindet_occ_int(self):
        # Create and cache dictionaries mapping spin-orbital indices to determinants \in psi_i to associated indices
        return self.get_spindet_a_occ_spindet_b_occ(self.psi_i)


#   _   _                 _ _ _              _
#  | | | |               (_) | |            (_)
#  | |_| | __ _ _ __ ___  _| | |_ ___  _ __  _  __ _ _ __
#  |  _  |/ _` | '_ ` _ \| | | __/ _ \| '_ \| |/ _` | '_ \
#  | | | | (_| | | | | | | | | || (_) | | | | | (_| | | | |
#  \_| |_/\__,_|_| |_| |_|_|_|\__\___/|_| |_|_|\__,_|_| |_|
#
#   _____                           _
#  |  __ \                         | |
#  | |  \/ ___ _ __   ___ _ __ __ _| |_ ___  _ __
#  | | __ / _ \ '_ \ / _ \ '__/ _` | __/ _ \| '__|
#  | |_\ \  __/ | | |  __/ | | (_| | || (_) | |
#   \____/\___|_| |_|\___|_|  \__,_|\__\___/|_|
#


class Hamiltonian_generator(object):
    """Generator class for matrix Hamiltonian; compute matrix elements of H
    in the basis of Slater determinants in a distributed fashion.
    Each rank handles local H_i \in len(psi_local) x len(psi_internal) chunk of the full H.
    Slater-Condon rules are used to compute the matrix elements <I|H|J> where I
    and J are Slater determinants.

    Called and re-created at each CIPSI iteration; i.e. each time determinants
    are added to the internal wave-function.

    :param comm: MPI.COMM_WORLD communicator
    :param E0: Float, energy
    :param d_one_e_integral: Dictionary of one-electorn integrals
    :param d_two_e_integral: Dictionary of two-electorn integrals
    :param driven_by: generate H in a an integral/determinant-driven fashion.

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
    * Matrix elements of H are stored as a hash lookup.
    """

    # Only pass internal determinant, since we'll only want to cache the Hamiltonian matrix elts. for an iteration
    # For ex., we iterate through the (psi_int) x (psi_ext) matrix elts. once to compute the PT2 contribution
    def __init__(
        self,
        comm,
        E0: Energy,
        d_one_e_integral: One_electron_integral,
        d_two_e_integral: Two_electron_integral,
        psi_internal: Psi_det,
        driven_by="determinant",
    ):
        self.comm = comm
        self.world_size = self.comm.Get_size()  # No. of processes running
        self.rank = self.comm.Get_rank()  # Rank of current process
        self.MPI_master_rank = 0  # Master rank
        # Full problem size is no. of internal determinants
        self.full_problem_size = len(psi_internal)
        # Save lists of determinants/integral dictionaries with instance of class
        self.psi_internal = psi_internal
        self.E0 = E0
        self.d_one_e_integral = d_one_e_integral
        self.d_two_e_integral = d_two_e_integral
        self.driven_by = driven_by

    @cached_property
    def distribution(self):
        """
        >>> h = Hamiltonian_generator(MPI.COMM_WORLD, 0, None, None, [0]*100)
        >>> h.world_size = 3
        >>> h.distribution
        array([34, 33, 33], dtype=int32)
        >>> h = Hamiltonian_generator(MPI.COMM_WORLD, 0, None, None, [0]*101)
        >>> h.world_size = 3
        >>> h.distribution
        array([34, 34, 33], dtype=int32)
        >>> h = Hamiltonian_generator(MPI.COMM_WORLD, 0, None, None, [0]*102)
        >>> h.world_size = 3
        >>> h.distribution
        array([34, 34, 34], dtype=int32)
        """
        # At initialization, each rank computes distribution of determinants
        floor, remainder = divmod(self.full_problem_size, self.world_size)
        ceiling = floor + 1
        return np.array([ceiling] * remainder + [floor] * (self.world_size - remainder), dtype="i")

    @cached_property
    def local_size(self):
        # At initialization, each rank computes distribution of determinants
        return self.distribution[self.rank]

    @cached_property
    def offsets(self):
        """
        >>> __test__= { "Hamiltonian_generator.offsets": Hamiltonian_generator.offsets }
        >>> h = Hamiltonian_generator(MPI.COMM_WORLD, 0, None, None, [0]*100)
        >>> h.world_size = 3
        >>> h.offsets
        array([ 0, 34, 67], dtype=int32)
        """
        # Compute offsets (start of the local section) for all nodes
        A = np.zeros(self.world_size, dtype="i")
        np.add.accumulate(self.distribution[:-1], out=A[1:])
        return A

    @cached_property
    def psi_local(self):
        # TODO: Right now, having each rank do this. Will re-do each iteration, but can be optimized somehow
        # Each rank computes local determinants
        return self.psi_internal[
            self.offsets[self.rank] : (self.offsets[self.rank] + self.distribution[self.rank])
        ]

    @cached_property
    def N_orb(self):
        key = max(self.d_two_e_integral)
        return max(compound_idx4_reverse(key)) + 1

    # Create instances of 1e and 2e `driver' classes
    @cached_property
    def Hamiltonian_1e_driver(self):
        return Hamiltonian_one_electron(self.d_one_e_integral, self.E0)

    @cached_property
    def Hamiltonian_2e_driver(self):
        if self.driven_by == "determinant":
            return Hamiltonian_two_electrons_determinant_driven(self.d_two_e_integral)
        elif self.driven_by == "integral":
            return Hamiltonian_two_electrons_integral_driven(self.d_two_e_integral)
        else:
            raise NotImplementedError

    # ~ ~ ~
    # H_ii
    # ~ ~ ~
    def H_ii(self, det_i: Determinant) -> Energy:
        # Diagonal elements of local Hamiltonian
        return self.Hamiltonian_1e_driver.H_ii(det_i) + self.Hamiltonian_2e_driver.H_ii(det_i)

    @cached_property
    def D_i(self):
        """Return `diagonal' of local H_i. (Diagonal meaning, entries of H_i
        corresponding to the diagonal part of H) as a numpy vector.
        Used for pre-conditioning step in Davidson's iteration."""
        D_i = np.zeros(self.local_size, dtype="float")
        # Iterate through local determinants m
        for j, det in enumerate(self.psi_local):
            D_i[j] = self.H_ii(det)
        return D_i

    # ~ ~ ~
    # H
    # ~ ~ ~
    @cached_property
    def H_i(self):
        """Build row-wise portion of Hamiltonian matrix (H_i).
        :return H_i: len(self.psi_local) \times len(self.psi_j), as numpy array"""
        H_i_1e = self.Hamiltonian_1e_driver.H(self.psi_local, self.psi_internal)
        H_i_2e = self.Hamiltonian_2e_driver.H(self.psi_local, self.psi_internal)
        return H_i_1e + H_i_2e

    @cached_property
    def H(self):
        """Build full Hamiltonian matrix, H = [H_1; ...; H_N].
        Local portions are computed by each rank, gathered and sent to all."""
        H_i = self.H_i
        # TODO: Optimize this? Mostly using for testing so not a huge deal.
        # Size of sendbuff
        sendcounts = np.array(self.local_size * self.full_problem_size, dtype="i")
        recvcounts = None
        if self.rank == self.MPI_master_rank:
            # Size of recvbuff
            recvcounts = np.zeros(self.world_size, dtype="i")
        self.comm.Gather(sendcounts, recvcounts, root=self.MPI_master_rank)
        H_full = np.zeros((self.full_problem_size, self.full_problem_size), dtype="float")
        # Master process gathers and sends full matrix Hamiltonian
        self.comm.Gatherv(H_i, (H_full, recvcounts), root=self.MPI_master_rank)
        self.comm.Bcast(np.array(H_full, dtype="float"), root=self.MPI_master_rank)

        return H_full

    @cached_property
    def H_i_1e_matrix_elements(self):
        """Generate elements of H_i_1e (local row-wise portion of one-electron Hamiltonian).
        Elements are gathered `on-the-fly' at first iteration, and then cached in a dict to be re-used later.
        """
        H_i_1e_matrix_elements = defaultdict(int)
        for I, det_I in enumerate(self.psi_local):
            for J, det_J in enumerate(self.psi_internal):
                H_i_1e_matrix_elements[(I, J)] += self.Hamiltonian_1e_driver.H_ij(det_I, det_J)
        # Remove the default dict
        return dict(H_i_1e_matrix_elements)

    @cached_property
    def H_i_2e_matrix_elements(self):
        """Generate elements of H_i_1e (local row-wise portion of one-electron Hamiltonian).
        Elements are gathered `on-the-fly' at first iteration, and then cached in a dict to be re-used later.
        Works for integral-driven or determinant-driven implementation.
        """
        H_i_2e_matrix_elements = defaultdict(int)
        for (I, J), idx, phase in self.Hamiltonian_2e_driver.H_indices(
            self.psi_local, self.psi_internal
        ):
            # Update (I, J)th 2e matrix element
            H_i_2e_matrix_elements[(I, J)] += phase * self.Hamiltonian_2e_driver.H_ijkl_orbital(
                *idx
            )
        # Remove the default dict
        return dict(H_i_2e_matrix_elements)

    # TODO:
    # H * G
    # ( \sum H_i) * G # We do that for now
    # \sum (H_i * G) # H_i big enough to fit in memory

    def H_i_implicit_matrix_product(self, M):
        """Function to implicitly compute matrix-matrix product W_i = H_i * M
        At first call, matrix elements of H_i are built `on-the-fly'. Matrix elements are cached
        for later use, and iterated through to compute H_i * V implicitly.

        :param H_i: local (self.local_size \times n) row-wise portion of Hamiltonian (never explicitly formed)
        :param V:  (self.full_size \times k) diensional numpy array

        :return W_i: locally computed chunk of matrix-matrix product (self.local_size \times k), as a numpy array
        """

        def H_i_implicit_matrix_product_step(matrix_elements, M):
            # Implicitly compute the 1e/2e Hamiltonain matrix-matrix product W_i = H_i * M
            # :param matrix_elements: python dictionary of 1e or 2e Hamiltonian matrix elements
            if M.ndim == 1:  # Handle case when M is a vector
                M = M.reshape(len(M), 1)
            k = M.shape[1]  # Column dimension
            # Pre-allocate space for local brick of matrix-matrix product
            W_i = np.zeros((self.local_size, k), dtype="float")
            # Iterate through nonzero matrix elements to compute matrix-matrix product
            for (I, J), matrix_elt in matrix_elements.items():
                W_i[I, :] += matrix_elt * M[J, :]  # Update row I of W_i
            return W_i

        # On first call, these will do the same things regardless of the `driven_by' option
        # If option to cache, compute elements and store in a sparse representation, then multiply
        return H_i_implicit_matrix_product_step(
            self.H_i_1e_matrix_elements, M
        ) + H_i_implicit_matrix_product_step(self.H_i_2e_matrix_elements, M)


import inspect

__test__ = {}
for name, member in inspect.getmembers(Hamiltonian_generator):
    if type(member) == cached_property:
        __test__[f"Hamiltonian_generator.{name}"] = member

#  ______            _     _
#  |  _  \          (_)   | |
#  | | | |__ ___   ___  __| |___  ___  _ __
#  | | | / _` \ \ / / |/ _` / __|/ _ \| '_ \
#  | |/ / (_| |\ V /| | (_| \__ \ (_) | | | |
#  |___/ \__,_| \_/ |_|\__,_|___/\___/|_| |_|
#
#


class Davidson_manager(object):
    """A matrix-free implementation of Davidson's method in parallel.
    All matrix products involving the Hamiltonian matrix are computed implicitly, and
    matrix entries are cached if memory allows.

    References:
    * `A Parallel Davidson-Type Algorithm for Several Eigenvalues' [L. Borges, S. Oliveira, 1998]
    * `The Davidson Method' [M. Crouzeix, B. Philippe, M. Sadkane, 1994]

    Each process will have local access to instance of the `Hamiltonian_generator()' class, to construct
    the local portion Hamiltonian on the fly.
    """

    def __init__(self, comm, H_i_generator: Hamiltonian_generator):
        self.comm = comm
        self.world_size = self.comm.Get_size()  # No. of processes running
        self.rank = self.comm.Get_rank()  # Rank of current process
        self.MPI_master_rank = 0  # Master rank
        # Instance of generator class for building local portion of the Hamiltonian
        self.H_i_generator = H_i_generator
        # TODO: Is there a best practice with this sort of thing? (Computing dist. of work and the like)
        # Hamiltonian_generator computes dist. of work, so pass these to this class for easier reference.
        self.full_problem_size = H_i_generator.full_problem_size
        self.distribution = H_i_generator.distribution
        self.offsets = H_i_generator.offsets
        self.local_size = H_i_generator.local_size

    def parallel_iteration_restart(self, dim_S, n_eig, n_newvecs, X_ik, V_ik, W_ik):
        """Restart Davidson's iteration; resize the trial subspace V_k
        and its associated data structures. Prevent a significant
        blow-up of column dimension.

        :param dim_S: column-size of local working variables (V_ik and friends)
        :param n_eig: number of eigenvalues to look for (minimally allowed dim_S)
        :param n_newvecs: number of new vectors added at the previous iteration
        :param X_ik: current Ritz vectors, numpy array
        :param V_ik, W_ik: local working variables, numpy arrays

        :return new values for dim_S, V_ik, and W_ik following implicit restart
        """
        if n_newvecs == 0:
            V_inew = X_ik[:, :n_eig]
        else:
            V_inew = np.c_[X_ik[:, :n_eig], V_ik[:, -n_newvecs:]]
        # Take leading n_eig Ritz vectors as new guess vectors
        dim_S = V_inew.shape[1]  # New subspace dimension
        V_ik = np.zeros((self.local_size, 0), dtype="float")
        W_ik = np.zeros((self.local_size, 0), dtype="float")
        # Initialize; normalize first basis vector
        v_inew = np.array(V_inew[:, 0], dtype="float")
        v_new = np.zeros(self.full_problem_size, dtype="float")
        self.comm.Allgatherv(
            [v_inew, MPI.DOUBLE], [v_new, self.distribution, self.offsets, MPI.DOUBLE]
        )
        V_ik = np.c_[V_ik, v_inew / np.linalg.norm(v_new)]
        for j in range(1, dim_S):
            # Orthogonalize next vector against previous ones in restart basis
            v_inew, norm_vnew = self.mgs(V_ik[:, :j], V_inew[:, j])
            V_ik = np.c_[V_ik, v_inew]  # Update basis
        n_newvecs = dim_S
        return dim_S, n_newvecs, V_ik, W_ik

    def mgs(self, V_ik, t_ik):
        """Parallel implementation of Modified Graham-Schmidt (MGS).
        Takes piece of new guess vector t_ik, and orthogonalizes it against trial subspace V_k.

        :param V_ik: local work variable, numpy matrix
        :param t_ik: local work variable, numpy vector

        :return orthonormalized vector t_ik
        """
        for j in range(V_ik.shape[1]):  # Iterate through k basis vectors
            c_ij = np.copy(
                np.inner(V_ik[:, j], t_ik)
            )  # Each process computes partial inner-product
            c_j = np.zeros(1, dtype="float")  # Pre-allocate
            self.comm.Allreduce([c_ij, MPI.DOUBLE], [c_j, MPI.DOUBLE])  # Default op=SUM
            t_ik = t_ik - c_j * V_ik[:, j]  # Remove component of t_ik in V_ik
        t_k = np.zeros(
            self.full_problem_size, dtype="float"
        )  # Pre-allocate space to receive new guess vector
        self.comm.Allgatherv([t_ik, MPI.DOUBLE], [t_k, self.distribution, self.offsets, MPI.DOUBLE])
        norm_tk = np.linalg.norm(t_k)
        return t_ik / norm_tk, norm_tk  # Return new orthonormalized vector

    def preconditioning(self, D_i, l_k, r_ik):
        """Preconditon next guess vector

        :param D_i: diagonal portion of local Hamiltonian, as a numpy vector
        :param l_k: an eigenvalue, as a scalar
        :param r_ik: residual, a numpy vector

        :return numpy vector
        """
        # Build diagonal preconditioner
        M_k = np.diag(np.clip(np.reciprocal(D_i - l_k), a_min=-1e5, a_max=1e5))
        return np.dot(M_k, r_ik)

    def print_master(self, str_):
        """Master rank prints inputted str"""
        if self.rank == self.MPI_master_rank:
            print(str_)

    def initial_guess_vectors(self, n, dim_S):
        """Generate standard initial guess vectors for Davidson's iteration.
        Locally distributed canonical basis vectors

        :param n: full problem size
        :param dim_S: initial subspace dimension
        """
        I = np.eye(n, dim_S)
        V_iguess = I[
            self.offsets[self.rank] : (self.offsets[self.rank] + self.distribution[self.rank]), :
        ]

        return V_iguess

    def distributed_davidson(
        self, V_iguess=None, n_eig=1, conv_tol=1e-8, subspace_tol=1e-10, max_iter=1000, m=1, q=100
    ):
        """Davidson's method implemented in parallel. The Hamiltonian
        matrix is distrubted row-wise across MPI rank.
        Finds the n_eig smallest eigenvalues of a symmetric Hamiltonian.

        :param H: self.full_problem_size \times self.full_problem_size symmetric Hamiltonian
        :param H_i: self.local_size \times self.full_problem_size `short and fat' locally distributed H
        :param V_iguess: self.local_size \times dim_S initial guess vectors
        :param n_eig: number of desired eigenpairs
        :param conv_tol: convergence tolerance
        :param subspace_tol: tolerance for adding new basis vectors to trial subspace (avoids ill-conditioning)
        :param max_iter: max no. of iterations for Davidson to run
        :param m: minimal subspace dimension, m <= dim_S
        :param q: memory footprint tuning, q is maximally allowed subspace dimension

        :return a list of `n_eig` eigenvalues/associated eigenvectors, as numpy vector/array resp.
        """
        # Initialization steps
        n = self.full_problem_size  # Save full problem size
        # Establish local vars: trial subspace (V_ik) and action of H_i on full V_k (W_ik = H_i * V_k)
        V_ik = np.zeros((self.local_size, 0), dtype="float")
        W_ik = np.zeros((self.local_size, 0), dtype="float")
        # Set initial guess vectors and minimal initial subspace dimension
        dim_S = min(m, n)
        assert m >= n_eig  # No. of initial guess vectors must be >= no. of desired energy values
        # Set initial guess vectors TODO: For now, have some default guess vectors for testing
        if V_iguess is None:
            V_iguess = self.initial_guess_vectors(n, dim_S)
        else:  # Else, check dimensions of initial guess vectors align with other inputs
            assert (n, m) == V_iguess.shape
        V_ik = np.c_[V_ik, V_iguess]
        # Build `diagonal` of local Hamiltonian
        D_i = self.H_i_generator.D_i

        n_newvecs = dim_S  # No. of vectors added is initial subspace dimension
        restart = True
        for k in range(1, max_iter):
            self.print_master(
                f"Process rank: {self.rank}, Iterate: {k}, Subspace dimension: {dim_S}"
            )
            # Gather full trial vectors added during previous iteration on each rank
            V_new = np.zeros((n, n_newvecs), dtype="float")
            V_inew = np.array(V_ik[:, -n_newvecs:], dtype="float")
            self.comm.Allgatherv(
                [V_inew, MPI.DOUBLE],
                [
                    V_new,
                    n_newvecs * np.array(self.distribution),
                    n_newvecs * np.array(self.offsets),
                    MPI.DOUBLE,
                ],
            )
            # Compute new columns of W_ik, W_inew = H_i * V_new
            # TODO: Some maximal allowed dimension before we switch to on the fly?
            W_inew = self.H_i_generator.H_i_implicit_matrix_product(V_new)  # Default is to cache
            W_ik = np.c_[W_ik, W_inew]

            # Each rank computes partial update to the projected Hamiltonian S_k
            if restart:  # If True, need to compute full S_k explicitly
                S_ik = np.dot(V_ik.T, W_ik)
                restart = False
            else:  # Else, append new rows & columns
                S_inew_c = np.dot(V_ik[:, :-n_newvecs].T, W_inew)
                S_ik = np.c_[S_ik, S_inew_c]
                S_inew_r = np.c_[np.dot(V_inew.T, W_ik[:, :-n_newvecs]), np.dot(V_inew.T, W_inew)]
                S_ik = np.r_[S_ik, S_inew_r]
            # Reduce contributions and form new S_k
            S_k = np.zeros((dim_S, dim_S), dtype="float")
            self.comm.Allreduce([S_ik, MPI.DOUBLE], [S_k, MPI.DOUBLE])
            # All ranks diagonalize S_k (dim_S kept small, so inexpensive)
            L_k, Y_k = np.linalg.eigh(S_k)  # TODO: Some check that this is symmetric?
            L_k, Y_k = L_k[:n_eig], Y_k[:, :n_eig]

            n_newvecs = 0  # Initialize counter; no. of new vectors added to trial subspace
            X_ik = np.dot(V_ik, Y_k)  # Pre-compute Ritz vectors (V_ik updated each iteration)
            # Each rank computes local portion of residuals simultaneously
            R_i = np.dot(W_ik, Y_k) - np.dot(X_ik, np.diag(L_k))
            R = np.zeros((n, n_eig), dtype="float")  # Pre-allocate space for residuals
            self.comm.Allgatherv(
                [R_i, MPI.DOUBLE],
                [
                    R,
                    n_eig * np.array(self.distribution),
                    n_eig * np.array(self.offsets),
                    MPI.DOUBLE,
                ],
            )  # Gather full residuals on each rank to compute norm
            # Track converged eigenpairs; True if R[:, j] < eps -> jth pair has converged
            converged, working_indices = [], []
            for j in range(n_eig):
                res = np.linalg.norm(R[:, j])
                self.print_master(f"||r_j||: {res}")
                converged.append(res < conv_tol)
                # If jth eigenpair not converged, add to list of working indices
                if not (res < conv_tol):
                    working_indices.append(j)
                else:
                    self.print_master(
                        f"Eigenvalue {j}: {L_k[j]} converged, no new trial vector added"
                    )

            if all(converged):  # Convergence check
                self.print_master("All eigenvalues converged, exiting iteration")
                break
            for j in working_indices:  # Iterate through non-converged eigenpairs
                self.print_master(
                    f"Eigenvalue {j}: not converged, preconditioning next trial vector"
                )
                # Precondition next trial vector
                t_ik = self.preconditioning(D_i, L_k[j], R_i[:, j])
                # Orthogonalize new trial vector against previous basis vectors via parallel-MGS
                t_k = np.zeros(n, dtype="float")
                self.comm.Allgatherv(
                    [np.array(t_ik, dtype="float"), MPI.DOUBLE],
                    [t_k, self.distribution, self.offsets, MPI.DOUBLE],
                )
                t_ik = t_ik / np.linalg.norm(t_k)
                t_ik, norm_tk = self.mgs(V_ik, t_ik)
                # If new trial vector is `small`, ignore. Avoids ill-conditioning
                if norm_tk > subspace_tol:
                    V_ik = np.c_[V_ik, t_ik]  # Append new vector to trial subspace
                    n_newvecs += 1

            dim_S = V_ik.shape[1]  # Update dimension of trial subspace

            if q <= dim_S:  # Collapose trial basis
                self.print_master(f"q <= dim_S: {dim_S}, restarting Davidson's")
                dim_S, n_newvecs, V_ik, W_ik = self.parallel_iteration_restart(
                    dim_S, n_eig, n_newvecs, X_ik, V_ik, W_ik
                )
                restart = True  # Indicate restart

            elif n_newvecs == 0:
                self.print_master(
                    "No new vectors added at previous iteration, restarting Davidson's"
                )
                dim_S, n_newvecs, V_ik, W_ik = self.parallel_iteration_restart(
                    dim_S, n_eig, n_newvecs, X_ik, V_ik, W_ik
                )
                restart = True  # Indicate restart

        else:
            raise NotImplementedError("Davidson not converged")

        m = X_ik.shape[1]  # Same across all ranks
        X_k = np.zeros((n, m), dtype="float")
        # Gather Ritz vectors on all ranks
        self.comm.Allgatherv(
            [X_ik, MPI.DOUBLE],
            [X_k, m * np.array(self.distribution), m * np.array(self.offsets), MPI.DOUBLE],
        )

        return L_k, X_k


#  _                  _
# |_) _        _  ._ |_) |  _. ._ _|_
# |  (_) \/\/ (/_ |  |   | (_| | | |_
#


class Powerplant_manager(object):
    """Class to compute all Energy associated with psi_internal (Psi_det);
    E denotes the variational energy <psi_det|H|psi_det>.
    E_PT2 denotes the PT2 contribution for the connected determinants."""

    # Generator class for current basis of determinants
    # Each rank has instance of this corresponding to locally stored dets psi_local \subset psi_internal
    def __init__(self, comm, H_i_generator: Hamiltonian_generator):
        self.comm = comm
        self.world_size = self.comm.Get_size()  # No. of processes running
        self.rank = self.comm.Get_rank()  # Rank of current process
        self.MPI_master_rank = 0  # Master rank
        self.H_i_generator = H_i_generator
        # Hamiltonian_generator computes dist. of work, so pass these to this class for easier reference.
        self.full_problem_size = H_i_generator.full_problem_size
        self.internal_distribution = H_i_generator.distribution
        # Offsets + distribution used for distributed computation of E_var
        self.internal_offsets = H_i_generator.offsets
        self.psi_internal = self.H_i_generator.psi_internal
        self.N_orb = self.H_i_generator.N_orb

    @cached_property
    def DM(self):
        # Instance of Davidson_manager() class for diagonalizing the Hamiltonian
        return Davidson_manager(self.comm, self.H_i_generator)

    @property
    def E_and_psi_coef(self) -> Tuple[Energy, Psi_coef]:
        """Diagonalize Hamiltonian in // and return ground state energy (new E) and corresponding eigenvector (new psi_coef)
        Done per CIPSI iteration"""
        try:
            energies, coeffs = self.DM.distributed_davidson()
        except NotImplementedError:
            print("Davidson Failed, fallback to numpy eigh")
            psi_H_psi = self.lewis.H  # Build full Hamiltonian
            energies, coeffs = np.linalg.eigh(psi_H_psi)

        E, psi_coef = energies[0], coeffs[:, 0]
        return E, psi_coef

    def E(self, psi_coef: Psi_coef) -> Energy:
        """Compute the variatonal energy associated with psi_det

        :param psi_coef: list of determinant coefficients in expansion of trial WF

        We assume the wavefunction is normalized; np.linalg.norm(c) = 1.
        Each rank will necessarily have access to the full list of determinant coefficients
        Vector * Vector.T * Matrix, distributed matrix inner product"""
        c = np.array(psi_coef, dtype="float")  # Coef. vector as np array
        # Compute local portion of matrix * vector product H_i * |psi_det>
        H_i_psi_det = self.H_i_generator.H_i_implicit_matrix_product(c)
        # Each rank computes portion of Vector.T * Vector inner-product (E_i, portion of variational energy)
        # Get coeffs. of local determinants
        c_i = c[
            self.internal_offsets[self.rank] : (
                self.internal_offsets[self.rank] + self.internal_distribution[self.rank]
            )
        ]
        E_i = np.copy(np.dot(c_i.T, H_i_psi_det))
        E = np.zeros(1, dtype="float")  # Pre-allocate
        self.comm.Allreduce(
            [E_i, MPI.DOUBLE], [E, MPI.DOUBLE]
        )  # Default op=SUM, reduce contributions
        # All ranks return varitonal energy
        # TODO: Fix this if there's a more efficient way to convert to a float
        return E.item()

    def gen_local_constraints(self) -> Iterator[Tuple[OrbitalIdx, ...]]:
        # Generate local constraints
        # Call to MPI function that yields local constraints
        C_loc, _ = dispatch_local_constraints(self.comm, self.psi_internal, self.N_orb)
        for C in C_loc:
            yield C

    def psi_external_pt2(
        self, C: Tuple[OrbitalIdx, ...], psi_coef: Psi_coef, E_var: Energy
    ) -> List[Energy]:
        """
        Compute the E_pt2 contributions of a subset of the connected space determined by given constraiant C
        The individual pt2 contribution of each connected det |J⟩ is given by
            E_pt2_J = ⟨Ψ(n)∣H∣∣J⟩^2 / ( E(n)−⟨J∣H∣∣J⟩ )

        Inputs:
        :param C: (Triplet) constraint |C⟩ = |a_0 a_1 a_2⟩-> Specify the three highest occupied alpha spin orbitals
                  This function only generates determinants |C⟩ (and the corresponding E_pt2 contributions)
                  s.to C (i.e., only generate connected dets occupied in orbitals a_0, a_1, a_2)
        :param psi_coef: list of determinant coefficients in expansion of trial WF

        Outputs:
        List of energies, Jth entry contains E_pt2 contribution of determinant |J⟩ \in connected space s.to |C⟩
        """

        # Compute len(psi_internal) \times len(psi_external_chunk) `Hamiltonian'
        # Each rank computes its contributions in place, these are then gathered to compute the full pt2 energy in self.E_pt2
        c = np.array(psi_coef, dtype="float")  # Coef. vector as np array
        # Pre-allocate space for nominators of E_pt2 contributions (as dict for now)
        nominator_conts_table = defaultdict(int)
        # Two-electron matrix elements

        # By constraint:
        # for C in constraints:
        #   for I, J in gen_connected_by_constraint(psi_internal, C):
        #       E_pt2_J <- (|J⟩, c[I]* <I|H|J>)
        # Store pairs of (|J⟩, E_pt2_J) -> By end of inner loop, partial contribution of |J⟩ to E_pt2 is fully computed
        # As in [Tubman et al., `18] they instead store individual numerator conts separately, do a sort by bistring, then aggregate across bitstrings

        if self.H_i_generator.driven_by == "determinant":
            # Pass over internal determinants
            for I, det_I in enumerate(self.psi_internal):
                # Inner pass (for each |I⟩) generates all excitations satisfying constraint |C⟩ from |I⟩
                # Triplet constrained singles
                for det_J in det_I.triplet_constrained_single_excitations_from_det(C, self.N_orb):
                    for idx, phase in self.H_i_generator.Hamiltonian_2e_driver.H_ij_indices(
                        det_I, det_J
                    ):
                        nominator_conts_table[det_J] += (
                            c[I]
                            * phase
                            * self.H_i_generator.Hamiltonian_2e_driver.H_ijkl_orbital(*idx)
                        )
                    nominator_conts_table[det_J] += c[
                        I
                    ] * self.H_i_generator.Hamiltonian_1e_driver.H_ij(det_I, det_J)
                # Triplet-constrained doubles
                for det_J in det_I.triplet_constrained_double_excitations_from_det(C, self.N_orb):
                    for idx, phase in self.H_i_generator.Hamiltonian_2e_driver.H_ij_indices(
                        det_I, det_J
                    ):
                        nominator_conts_table[det_J] += (
                            c[I]
                            * phase
                            * self.H_i_generator.Hamiltonian_2e_driver.H_ijkl_orbital(*idx)
                        )
        elif self.H_i_generator.driven_by == "integral":
            for (I, det_J), idx, phase in self.H_i_generator.Hamiltonian_2e_driver.H_indices_pt2(
                self.psi_internal, C
            ):
                nominator_conts_table[det_J] += (
                    c[I] * phase * self.H_i_generator.Hamiltonian_2e_driver.H_ijkl_orbital(*idx)
                )
            # One-electron matrix elements
            for I, det_I in enumerate(self.psi_internal):
                # Inner pass (for each |I⟩) generates all excitations satisfying constraint |C⟩ from |I⟩
                # Triplet constrained singles
                # Each det_J will show up all connected to multiple I.. so have to do this outside of integral loop
                for det_J in det_I.triplet_constrained_single_excitations_from_det(C, self.N_orb):
                    nominator_conts_table[det_J] += c[
                        I
                    ] * self.H_i_generator.Hamiltonian_1e_driver.H_ij(det_I, det_J)
        else:
            raise NotImplementedError

        # Remove contributions of internal determinants
        for det_I in self.psi_internal:
            if det_I in nominator_conts_table:
                del nominator_conts_table[det_I]
        # `Sort and accumulate` E_pt2 contributions corresponding to individual dets ∣J⟩ done in place above...
        # Each item in (key, item) pair is the partial E_pt2 contribution of ∣J⟩ -> Denoted E_pt2_J

        E_pt2_J = nominator_conts_table.values()
        nominator_conts = np.array(list(E_pt2_J), dtype="float")
        # TODO: For integral driven, loop over integrals? In general, be more efficient in this area.
        # TODO: In general, though, we need a different way to do this. It goes back to storing the connected space. We can even do the denominator conts in a separate array..
        psi_connected_C = [det_J for det_J in nominator_conts_table.keys()]
        denominator_conts = np.divide(
            1.0,
            E_var - np.array([self.H_i_generator.H_ii(det_J) for det_J in psi_connected_C]),
        )

        # Compute E_pt2 contributions of this subset of connected space
        # Do this einsum in place, then Reduce later
        # Return the determinants we generated as well for the selection step
        return psi_connected_C, np.einsum(
            "i,i,i -> i", nominator_conts, nominator_conts, denominator_conts
        )  # vector * vector * vector -> scalar

    def E_pt2(self, psi_coef: Psi_coef) -> Energy:
        """
        Computes the E_pt2 contributions of each connected determinant split across MPI ranks
        E_pt2 energies are computed in `chunks' of size L at a time, then Reduced

        Inputs:
        :param psi_coef: list of determinant coefficients in expansion of trial WF

        Output:
        E_pt2 value for the current CIPSI iteration, as a float
        """

        # Pre-allocate space for the reduced E_pt2 contributions
        E_var = self.E(psi_coef)  # Pre-compute variational energy
        E_pt2_conts = np.zeros(1, dtype="double")
        # Generate chunks of the connected space by constraints
        for C in self.gen_local_constraints():
            # Track E_pt2 contributions of determinants in the current chunk of the connected space
            _, E_pt2_conts_local = self.psi_external_pt2(C, psi_coef, E_var)
            E_pt2_conts += sum(E_pt2_conts_local)

        # Sum in place -> MPI.Allreduce call
        # Equivalent to MPI AllGather + sum. Do this because we can't store the full external space
        _E_pt2 = np.zeros(1, dtype="double")  # Pre-allocate recvbuf for final E_pt2 value
        self.comm.Allreduce([E_pt2_conts, MPI.DOUBLE], [_E_pt2, MPI.DOUBLE])

        return _E_pt2.item()


#  __
# (_   _  |  _   _ _|_ o  _  ._
# __) (/_ | (/_ (_  |_ | (_) | |
#

# First, we have functions that do the selection


def selection_step(
    comm,
    lewis: Hamiltonian_generator,
    n_ord,
    psi_coef: Psi_coef,
    psi_det: Psi_det,
    n,
) -> Tuple[Energy, Psi_coef, Psi_det]:
    # 1. Each MPI rank has a subset of constraints and computes E_pt2 contributions of determinants in this constraint (disjoint partitioning)
    # 2. Take the n determinants (across ranks) who have the biggest contribution and add it the wave function psi
    # 3. Diagonalize H corresponding to this new wave function to get the new variational energy, and new psi_coef

    # In the main code:
    # -> Go to 1., stop when E_pt2 < Threshold || N < Threshold
    # See example of chained call to this function in `test_f2_631g_1p5p5det`

    # Instance of Powerplant manager class for computing E_pt2 energies
    PP_manager = Powerplant_manager(comm, lewis)

    # Each rank generates a chunk of the external space at the time -> computes the E_pt2 contributions of its respective chunk
    # Compute the n (local) best contributions on each rank -> Allgather + partial sort to get n global best across ranks

    # 1.
    # Compute the local best E_pt2 contributions + associated dets
    local_best_dets, local_best_energies = local_sort_pt2_energies(PP_manager, psi_coef, psi_det, n)

    # 2.
    # Global sort local contributions to get global best E_pt2 contributions + dets
    global_best_dets = global_sort_pt2_energies(comm, local_best_dets, local_best_energies, n)

    # 3.
    # Add `best' determinants to the trial wavefunction
    psi_det_extented = psi_det + global_best_dets

    # 4.
    # New instance of Hamiltonian manager class for the extended wavefunction
    lewis_new = Hamiltonian_generator(
        comm,
        lewis.E0,
        lewis.d_one_e_integral,
        lewis.d_two_e_integral,
        psi_det_extented,
    )

    # Return new E_var, psi_coef, and extended wavefunction
    return (*Powerplant_manager(comm, lewis_new).E_and_psi_coef, psi_det_extented)


def local_sort_pt2_energies(
    PP_manager: Powerplant_manager, psi_coef: Psi_coef, psi_det: Psi_det, n
):
    # Function to compute the local n best E_pt2 contributions
    # Each rank computes the best contributions from a (disjoint) subset of the connected space, determined by constraint

    # Pre-allocate space to track bests from previous chunk
    E_var = PP_manager.E(psi_coef)
    # PT2 contribution are always < 0, use 1 as a tombstone value; these will never be selected
    local_best_energies = np.ones(n, dtype="float")
    # TODO: Will have to think more carefully about the case when size of the constraint space is < n
    # `Dummy' determinants, corresponding to local_best_energies = 1
    local_best_dets = [Determinant((), ())] * n

    for C in PP_manager.gen_local_constraints():
        # 1.
        # Compute E_pt2 contributions of current chunk of determinants
        # It is assumed that `chunk_size` is enough to fit in memory
        psi_connected_C, E_pt2_energies_C = PP_manager.psi_external_pt2(C, psi_coef, E_var)

        # 2.
        # Aggregate current E_pt2 contributions and current n `best' contributions to partial sort
        if len(E_pt2_energies_C) > 0:
            working_energies = np.r_[E_pt2_energies_C, local_best_energies]
            working_dets = psi_connected_C + local_best_dets
        else:
            # Nothing generated; local best dets and energies remain the same... Pass to next constraint in loop
            continue

        # Update `local' n largest magnitude E_pt2 contributions from working chunk -> indices of top n determinants
        # E_pt2 < 0, so n `smallest' are actually the largest magnitude contributors
        local_idx = np.argpartition(working_energies, n)[:n]
        local_best_energies = np.array(working_energies[local_idx], dtype="float")
        # Get determinants that are the local best contributors
        local_best_dets = [working_dets[i] for i in local_idx]

    # Return n largest magnitude energies/dets from this rank
    return local_best_dets, local_best_energies


def global_sort_pt2_energies(comm, local_best_dets: Psi_det, local_best_energies, n):
    # MPI Gather call local bests -> partial sort to get n global best of these guys
    # Ugly, but at least we can store this in memory
    # Pre-allocate space + Gather locally best contributions on all ranks
    if comm.Get_size() > 1:
        aggregated_energies = np.zeros((comm.Get_size()) * n, dtype="float")
        comm.Allgather([local_best_energies, MPI.DOUBLE], [aggregated_energies, MPI.DOUBLE])
        # Lower-case MPI command for python objs
        aggregated_dets_ = comm.allgather(local_best_dets)
        # mpi4py gathers lists into a list of lists -> need to unpack into a single list
        aggregated_dets = list(chain.from_iterable(aggregated_dets_))
        # Partial sort gathered local bests -> `global' n largest mangitude E_pt2 contributions
        global_idx = np.argpartition(aggregated_energies, n)[:n]

        # Now, save global best E_pt2 contributors
        global_best_dets = [aggregated_dets[i] for i in global_idx]
    else:
        global_best_dets = local_best_dets

    # Return dets corresponding to globally `best' E_pt2 contributions
    return global_best_dets


# Next, we have functions that split the connected space


def get_chunk_of_connected_determinants(psi_det: Psi_det, n_orb: int, L=None) -> Iterator[Psi_det]:
    """
    MPI function, generates chunks of connected determinants of size L

    Inputs:
    :param psi_det: list of determinants
    :param L: integer, maximally allowed `chunk' of the conneceted space to yield at a time
    default is L = None, if no chunk size specified, a chunk of the connected space is allocated to each rank

    >>> d1 = Determinant((0, 1), (0,) ) ; d2 = Determinant((0, 2), (0,) )
    >>> for psi_chunk in get_chunk_of_connected_determinants( [ d1,d2 ], 4):
    ...     len(psi_chunk)
    22
    >>> for psi_chunk in get_chunk_of_connected_determinants( [ d1,d2 ], 4, 11 ):
    ...     len(psi_chunk)
    11
    11
    >>> for psi_chunk in get_chunk_of_connected_determinants( [ d1,d2 ], 4, 10 ):
    ...     len(psi_chunk)
    10
    10
    2
    """

    def gen_all_connected_determinant(psi_det: Psi_det, n_orb: int) -> Psi_det:
        """
        >>> d1 = Determinant((0, 1), (0,) ) ; d2 = Determinant((0, 2), (0,) )
        >>> len(gen_all_connected_determinant( [ d1,d2 ], 4 ))
        22

        We remove the connected determinant who are already inside the wave function. Order doesn't matter
        """
        # Literal programing
        # return set(chain.from_iterable(map(self.gen_all_connected_det_from_det, psi_det)))- set(psi_det)

        # Naive algorithm 13
        l_global = []
        for i, det in enumerate(psi_det):
            for det_connected in det.gen_all_connected_det(n_orb):
                # Remove determinant who are in psi_det
                if det_connected in psi_det:
                    continue
                # If it's was already generated by an old determinant, just drop it
                if any(det_connected.is_connected(d) for d in psi_det[:i]):
                    continue

                l_global.append(det_connected)

        # Return connected space
        return l_global

    # Naive: Each ranks generates all connected determinants, and takes what is theirs
    psi_connected = gen_all_connected_determinant(psi_det, n_orb)
    world_size = MPI.COMM_WORLD.Get_size()
    # TODO: len(psi_connected) will not scale, but is needed for this naive representation
    full_idx = np.arange(len(psi_connected))
    split_idx = np.array_split(full_idx, world_size)
    # Part of connected space available to each rank
    full_chunk = [psi_connected[i] for i in split_idx[MPI.COMM_WORLD.Get_rank()]]

    if L is None:  # If no argument passed by the user
        L = len(full_chunk)
    number_of_chunks, leftovers = divmod(len(full_chunk), L)
    # Yield chunks of size L one at a time
    for i in np.arange(number_of_chunks):
        yield full_chunk[i * L : (i + 1) * L]
    # Yield `leftover' determinants (size of chunk < L)
    if leftovers > 0:  # If there are leftover determinants to handle
        yield full_chunk[number_of_chunks * L : number_of_chunks * L + leftovers]


def generate_all_constraints(n_elec: int, n_orb: int, m=3) -> List[Tuple[OrbitalIdx, ...]]:
    """Generate all `m'-constraints, characterized by m most highly occupied (usually alpha) electrons
    >>> generate_all_constraints(3, 4)
    [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    >>> len(generate_all_constraints(3, 6))
    20
    """
    # Problem of number of constraints reduces to binning m (= 3, usually) spin electrons into n_orb - (n_elec - m) orbitals...
    # We assume the bottom n_elec - m alpha-electrons are at the lowest ON, since only the top three matter
    # Then, just bin the last m among n_orb - (n_elec - m) remaining orbitals.
    if n_elec < m:
        raise NotImplementedError
    unfilled_orbs = [i for i in range(n_elec - m, n_orb)]
    return [constraint for constraint in combinations(unfilled_orbs, m)]


def check_constraint(det: Determinant, spin="alpha"):
    # Give me a determinant. What constraint does it satisfy? (What are three most highly occupied alpha spin orbitas)
    spindet = getattr(det, spin)
    # Return constraint as |Spin_determinant|
    return spindet[-3:]


def dispatch_local_constraints(
    comm: MPI.COMM_WORLD, psi: Psi_det, n_orb: int
) -> List[Tuple[OrbitalIdx, ...]]:
    """MPI function, perform static load balancing + distribution of triplet-constraints to MPI ranks
    Work is roughly distributed based on the number of connected determinants satisfying a particular constraint

    Inputs:
    :param psi: List of internal determinants (global)

    Outputs:
    :param C_loc: Local constraints"""

    rank = comm.Get_rank()
    # Initialize array to track workload of each rank
    W = np.zeros(shape=(comm.Get_size(),), dtype="i")
    C_loc = []  # Pre-allocate space for local constraints
    na = len(getattr(psi[0], "alpha"))  # No. of alpha electrons
    nb = len(getattr(psi[0], "beta"))  # No. of beta electrons
    # Pass through all triplet constraints to distribute
    H = []  # Track work dist.
    for C in generate_all_constraints(na, n_orb):
        B_upper = set(range(min(C) + 1, n_orb))  # Upper bitmask
        B_lower = set(range(min(C)))  # Lower bitmask
        h = 0  # Track work of this constraint
        for det in psi:
            det_a = getattr(det, "alpha")
            constraint_orbitals_occupied = set(det_a) & set(C)
            nonconstrained_orbitals_occupied = (set(det_a) & B_upper) - set(C)
            # n_particles = [np_a, np_b, np_aa, np_bb, np_ab]
            # Number of particles (or pairs) that (could possibly) involve an excitation satisfying C
            if len(constraint_orbitals_occupied) == 0:
                # No excitations will satisfy C -> Pass
                n_particles = np.zeros(5, dtype="i")
            elif len(constraint_orbitals_occupied) == 1:
                # To satisfy C, excitation must be aa (into empty constraint orbitals)
                n_particles = np.array([0, 0, 1, 0, 0], dtype="i")
            elif len(constraint_orbitals_occupied) == 2:
                # To satisfy C, only possible single is a, must excite into empty constraint orbital
                na_orbs_unocc_lower = B_lower - set(det_a)
                # No bb; for ab doubles, a must excite into empty constraint orbital, so 1 * (self.n_orb - nb) ab pairs
                n_particles = np.array([1, 0, len(na_orbs_unocc_lower), 0, (n_orb - nb)], dtype="i")
            elif len(constraint_orbitals_occupied) == 3:
                # To satisfy C, any a or aa excitaion into `lower` unoccupied alpha orbitals
                # All possible b or bb excitations satisfy C
                na_orbs_unocc_lower = B_lower - set(det_a)
                # Divide some things by 2 to avoid repeats due to permuation (e.g., (p1, p2) = (1, 2) <-> (p1, p2) = (2, 1))
                n_particles = np.array(
                    [
                        len(na_orbs_unocc_lower),
                        n_orb - nb,
                        len(na_orbs_unocc_lower) * (len(na_orbs_unocc_lower) - 1) / 2,
                        (n_orb - nb) * (n_orb - nb - 1) / 2,
                        (n_orb - nb) * len(na_orbs_unocc_lower),
                    ],
                    dtype="i",
                )

            # n_holes = [nh_a, nh_b, nh_aa, nh_bb, nh_ab]
            # Number of holes (or pairs) that (could possibly) involve an excitation satisfying C
            if len(nonconstrained_orbitals_occupied) > 2:
                # No excitations will satisfy C -> Pass
                n_holes = np.zeros(5, dtype="i")
            elif len(nonconstrained_orbitals_occupied) == 2:
                # To satisfy C, excitation must be aa (out of `higher` non-constraint orbitals)
                n_holes = np.array([0, 0, 1, 0, 0], dtype="i")
            elif len(nonconstrained_orbitals_occupied) == 1:
                # To satisfy C, only possible single is a, must excite out of `higher` constraint orbitals
                na_orbs_occ_lower = set(det_a) & B_lower
                # No bb; for ab doubles, a must excite out of `higher` constraint orbital, so 1 * nb ab pairs
                n_holes = [1, 0, len(na_orbs_occ_lower), 0, nb]
            elif len(nonconstrained_orbitals_occupied) == 0:
                # To satisfy C, can excite out of any `lower` occupied alpha orbitals
                # All possible b or bb excitations satisfy C
                na_orbs_occ_lower = set(det_a) & B_lower
                n_holes = [
                    len(na_orbs_occ_lower),
                    nb,
                    len(na_orbs_occ_lower) * (len(na_orbs_occ_lower) - 1) / 2,
                    nb * (nb - 1) / 2,
                    len(na_orbs_occ_lower) * nb,
                ]

            # Number of singly/doubly connected determinants to |det> satisfying constraint C
            #   Simply (per spin type) number of holes * particles that will yield an excitation in C
            h += np.dot(n_particles, n_holes)  # Add to work thus far

        if h:  # Handle case where no dets satisfy C.. No one will do it
            _, loc = comm.allreduce(
                (W[rank], rank), MPI.MINLOC
            )  # This is a tuple, so use python command
            if loc == rank:  # Rank with lowest amount of work collects current constraint
                C_loc.append(C)
                H.append(h)
                W[rank] += h  # Add h to the amount of `work` rank has

    # Return local constraints and distribution of work
    return C_loc, H
