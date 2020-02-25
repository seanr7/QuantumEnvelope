#!/usr/bin/env python3

# Types
# -----

from typing import Tuple, Dict, NewType, NamedTuple, List

# Orbital index (1,2,...,Norb)
OrbitalIdx = NewType('OrbitalIdx', int)


# Two-electron integral :
# $<ij|kl> = \int \int \phi_i(r_1) \phi_j(r_2) \frac{1}{|r_1 - r_2|} \phi_k(r_1) \phi_l(r_2) dr_1 dr_2$

Two_electron_integral = Dict[ Tuple[OrbitalIdx,OrbitalIdx,OrbitalIdx,OrbitalIdx], float]


# One-electron integral :
# $<i|h|k> = \int \phi_i(r) (-\frac{1}{2} \Delta + V_en ) \phi_k(r) dr$

One_electron_integral = Dict[ Tuple[OrbitalIdx,OrbitalIdx], float]

Determinant_Spin = Tuple[OrbitalIdx, ...]
class Determinant(NamedTuple):
    '''Slater determinant: Product of 2 determinants.
       One for $\alpha$ electrons and one for \beta electrons.'''
    alpha: Determinant_Spin
    beta: Determinant_Spin

# -------


from collections import defaultdict
from itertools   import product




# ~
# Integrals of the Hamiltonian over molecular orbitals
# ~


def load_integrals(fcidump_path) -> Tuple[int, Two_electron_integral, One_electron_integral]:
    '''Read all the Hamiltonian integrals from the data file.
       Returns: (E0, d_one_e_integral, d_two_e_integral).
       E0 : a float containing the nuclear repulsion energy (V_nn),
       d_one_e_integral : a dictionary of one-electron integrals,
       d_two_e_integral : a dictionary of two-electron integrals.
       '''
    
    with open(fcidump_path) as f:
        data_int = f.readlines()

    # Only non-zero integrals are stored in the fci_dump.
    # Hence we use a defaultdict to handle the sparsity
    d_one_e_integral = defaultdict(int)
    d_two_e_integral = defaultdict(int)
    for line in data_int[4:]:
        v, *l = line.split()
        v = float(v)
        # Transform from Mulliken (ik|jl) to Dirac's <ij|kl> notation
        # (swap indices)
        i,k,j,l = list(map(int, l)) 
 
        if i == 0:
            E0 = v
        elif j == 0:
            # One-electron integrals are symmetric (when real, not complex)
            d_one_e_integral[ (i,k) ] = v            
            d_one_e_integral[ (k,i) ] = v
        else:
            # Two-electron integrals have many permutation symmetries:
            # Exchange r1 and r2 (indices i,k and j,l)
            # Exchange i,k (if complex, with a minus sign)
            # Exchange j,l (if complex, with a minus sign)
            d_two_e_integral[ (i,j,k,l) ] = v
            d_two_e_integral[ (i,l,k,j) ] = v
            d_two_e_integral[ (j,i,l,k) ] = v
            d_two_e_integral[ (j,k,l,i) ] = v
            d_two_e_integral[ (k,j,i,l) ] = v
            d_two_e_integral[ (k,l,i,j) ] = v
            d_two_e_integral[ (l,i,j,k) ] = v
            d_two_e_integral[ (l,k,j,i) ] = v

    return E0, d_one_e_integral, d_two_e_integral


def H_one_e(i: OrbitalIdx, j: OrbitalIdx) -> float :
    '''One-electron part of the Hamiltonian: Kinetic energy (T) and
       Nucleus-electron potential (V_{en}). This matrix is symmetric.'''
    return d_one_e_integral[ (i,j) ]


def H_two_e(i: OrbitalIdx, j: OrbitalIdx, k: OrbitalIdx, l: OrbitalIdx) -> float:
    '''Assume that *all* the integrals are in the global_variable
       `d_two_e_integral` In this function, for simplicity we don't use any
       symmetry sparse representation.  For real calculations, symmetries and
       storing only non-zeros needs to be implemented to avoid an explosion of
       the memory requirements.'''
    return d_two_e_integral[ (i,j,k,l) ]





# Now, we consider the Hamiltonian matrix in the basis of Slater determinants.
# Slater-Condon rules are used to compute the matrix elements <I|H|J> where I
# and J are Slater determinants.
# 
# ~
# Slater-Condon Rules
# ~
#
# https://en.wikipedia.org/wiki/Slater%E2%80%93Condon_rules
# https://arxiv.org/abs/1311.6244
#
# * H is symmetric
# * If I and J differ by more than 2 orbitals, <I|H|J> = 0, so the number of
#   non-zero elements of H is bounded by N_det x ( N_alpha x (N_orb - N_alpha))^2,
#   where N_det is the number of determinants, N_alpha is the number of
#   alpha-spin electrons (N_alpha >= N_beta), and N_orb is the number of
#   molecular orbitals.  So the number of non-zero elements scales linearly with
#   the number of selected determinant.
#

def load_wf(path_wf) -> Tuple[ List[float] , List[Determinant] ]  :
    '''Read the input file :
       Representation of the Slater determinants (basis) and
       vector of coefficients in this basis (wave function).'''

    with open(path_wf) as f:
        data = f.read().split()

    def decode_det(str_):
        for i,v in enumerate(str_, start=1):
            if v == '+':
                yield i

    def grouper(iterable, n):
        "Collect data into fixed-length chunks or blocks"
        args = [iter(iterable)] * n
        return zip(*args)

    det = []; psi_coef = []
    for (coef, det_i, det_j) in grouper(data,3):
        psi_coef.append(float(coef))
        det.append ( Determinant( tuple(decode_det(det_i)), tuple(decode_det(det_j) ) ) )

    return psi_coef, det


def get_exc_degree(det_i: Determinant, det_j: Determinant) -> Tuple[int,int]:
    '''Compute the excitation degree, the number of orbitals which differ
       between the two determinants.
    >>> get_exc_degree(Determinant(alpha=(1, 2), beta=(1, 2)),
    ...                Determinant(alpha=(1, 3), beta=(5, 7)) )
    (1, 2)
    '''
    ed_up =  len(set(det_i.alpha).symmetric_difference(set(det_j.alpha))) // 2
    ed_dn =  len(set(det_i.beta).symmetric_difference(set(det_j.beta))) // 2
    return (ed_up, ed_dn)

def get_phase_idx_single_exc(det_i: Determinant_Spin, det_j: Determinant_Spin) -> Tuple[int,int,int]:
    '''phase, hole, particle of <I|H|J> when I and J differ by exactly one orbital
       h is occupied only in I
       p is occupied only in J'''
    
    h, = set(det_i) - set(det_j)
    p, = set(det_j) - set(det_i)

    phase=1
    for det, idx in ((det_i,h),(det_j,p)):
        for occ in det:
            phase = -phase
            if occ == idx:
                break
    return (phase,h,p)

def get_phase_idx_double_exc(det_i: Determinant_Spin, det_j: Determinant_Spin) -> Tuple[int,int,int,int,int]:
    '''phase, holes, particles of <I|H|J> when I and J differ by exactly two orbitals
       h1, h2 are occupied only in I
       p1, p2 are occupied only in J'''
    
    #Hole
    h1, h2 = sorted(set(det_i) - set(det_j))
    #Particle
    p1, p2 = sorted(set(det_j) - set(det_i))

    # Compute phase. See paper to have a loopless algorithm
    # https://arxiv.org/abs/1311.6244
    phase = 1
    for l_,mp in ( (det_i,h1), (det_j,p1),  (det_j,p2), (det_i,h2) ):
        for v in l_:
            phase = -phase
            if v == mp:
                break
    # https://github.com/QuantumPackage/qp2/blob/master/src/determinants/slater_rules.irp.f:299
#    a = min(h1, p1)
    b = max(h1, p1)
    c = min(h2, p2)
 #   d = max(h2, p2)
    #if ((a<c) and (c<b) and (b<d)):
    if (c<b):
        phase = -phase

    return (phase,h1,h2,p1,p2)



def H_i_i(det_i: Determinant) -> float:
    '''Diagonal element of the Hamiltonian : <I|H|I>.'''
    res  = sum(H_one_e(i,i) for i in det_i.alpha)
    res += sum(H_one_e(i,i) for i in det_i.beta)
    
    res += sum( (H_two_e(i,j,i,j) - H_two_e(i,j,j,i) ) for (i,j) in product(det_i.alpha, det_i.alpha)) / 2
    res += sum( (H_two_e(i,j,i,j) - H_two_e(i,j,j,i) ) for (i,j) in product(det_i.beta, det_i.beta)) / 2
       
    res += sum( H_two_e(i,j,i,j) for (i,j) in product(det_i.alpha, det_i.beta))
 
    return res


def H_i_j_single(li: Determinant_Spin, lj: Determinant_Spin, lk: Determinant_Spin) -> float:
    '''<I|H|J>, when I and J differ by exactly one orbital.'''
    # NOT TESTED /!\
    
    # Interaction 
    phase, m, p = get_phase_idx_single_exc(li,lj)
    res = H_one_e(m,p)

    res += sum ( H_two_e(m,i,p,i)  -  H_two_e(m,i,i,p) for i in li)
    res += sum ( H_two_e(m,i,p,i)  -  H_two_e(m,i,i,p) for i in lk)

    # Result    
    return phase*res


def H_i_j_doubleAA(li: Determinant_Spin, lj: Determinant_Spin) -> float:
    '''<I|H|J>, when I and J differ by exactly two orbitals within
       the same spin.'''

    phase,h1,h2,p1,p2 = get_phase_idx_double_exc(li,lj)
    #Hole
    i, j = sorted(set(li) - set(lj))
    #Particle
    k, l = sorted(set(lj) - set(li))

    res = ( H_two_e(h1,h2,p1,p2)  -  H_two_e(h1,h2,p2,p1) )

    return phase * res 


def H_i_j_doubleAB(det_i: Determinant, det_j: Determinant_Spin) -> float:
    '''<I|H|J>, when I and J differ by exactly one alpha spin-orbital and
       one beta spin-orbital.'''

    phaseA, hA, pA = get_phase_idx_single_exc(det_i.alpha,det_j.alpha)
    phaseB, hB, pB = get_phase_idx_single_exc(det_i.beta, det_j.beta)

    res =  H_two_e(hA,hB,pA,pB)
    
    return phaseA * phaseB * res 


def H_i_j(det_i: Determinant, det_j: Determinant) -> float:
    '''General function to dispatch the evaluation of H_ij'''

    ed_up, ed_dn = get_exc_degree(det_i, det_j)

    # Same determinant -> Diagonal element
    if ed_up + ed_dn == 0:
        return H_i_i(det_i)

    # Single excitation
    elif (ed_up, ed_dn) == (1, 0):
        return H_i_j_single(det_i.alpha, det_j.alpha, det_i.beta)
    elif (ed_up, ed_dn) == (0, 1):
        return H_i_j_single(det_i.beta, det_j.beta, det_i.alpha)

    # Double excitation of same spin
    elif (ed_up, ed_dn) == (2, 0):
        return H_i_j_doubleAA(det_i.alpha,det_j.alpha)
    elif (ed_up, ed_dn) == (0, 2):
        return H_i_j_doubleAA(det_i.beta,det_j.beta)

    # Double excitation of opposite spins
    elif (ed_up, ed_dn) == (1, 1):
        return H_i_j_doubleAB(det_i, det_j)

    # More than doubly excited, zero
    else:
        return 0.


if __name__ == "__main__":

    #fcidump_path='f2_631g.FCIDUMP'
    fcidump_path='kev.DSDKSL'
    wf_path='f2_631g.28det.wf'

    # Load integrals
    E0, d_one_e_integral, d_two_e_integral = load_integrals(fcidump_path)

    # Load wave function
    psi_coef, det = load_wf(wf_path)

    # Computation of the Energy of the input wave function (variational energy)
    E_var = sum(psi_coef[i] * psi_coef[j] * H_i_j(det_i,det_j, d_one_e_integral, d_two_e_integral)
                for (i,det_i),(j,det_j) in product(enumerate(det),enumerate(det)) )
    print (E0+E_var)
    expected_value = -198.71760085
    print ('expected value:', expected_value)
    print (E0+E_var  - expected_value)
    assert (E0+E_var == expected_value)

