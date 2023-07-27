import ctypes

qelib = ctypes.find_library("../../src/qe.so")

QELIB_SPIN_DET_TYPE_VECTOR = 0

qelib_qe_orbital_int_type = ctypes.c_uint32
qelib_qe_spin_det_vector_type = ctypes.c_void_p
qelib_qe_spin_det_generic_type = ctypes.c_void_p
qelib_int = ctypes.c_int

qelib.qe_spin_det_vector_create.argtypes = None
qelib.qe_spin_det_vector_create.restype = qelib_qe_spin_det_vector_type

qelib.qe_spin_det_vector_destroy.argtypes = [qelib_qe_spin_det_vector_type]
qelib.qe_spin_det_vector_destroy.restype = None

qelib.qe_spin_det_vector_xor.argtypes = [
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        ]
qelib.qe_spin_det_vector_xor.restype = qelib_int

qelib.qe_spin_det_vector_and.argtypes = [
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        ]
qelib.qe_spin_det_vector_and.restype = qelib_int

qelib.qe_spin_det_vector_or.argtypes = [
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        qelib_qe_spin_det_vector_type, 
        ]
qelib.qe_spin_det_vector_or.restype = qelib_int

qelib.qe_spin_det_vector_popcount.argtypes = [qelib_qe_spin_det_vector_type]
qelib.qe_spin_det_vector_popcount.restype = qelib_int

qelib.qe_spin_det_vector_apply_single_excitation.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_vector_apply_single_excitation.restype = qelib_int

qelib.qe_spin_det_vector_apply_double_excitation.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_vector_apply_double_excitation.restype = qelib_int

qelib.qe_spin_det_vector_exc_degree.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type
        ]

qelib.qe_spin_det_vector_exc_degree.restype = qelib_int

qelib.qe_spin_det_vector_get_holes.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type
        ]

qelib.qe_spin_det_vector_get_holes.restype = qelib_int

qelib.qe_spin_det_vector_get_particles.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type,
        qelib_qe_spin_det_vector_type
        ]

qelib.qe_spin_det_vector_get_particles.restype = qelib_int

qelib.qe_spin_det_vector_phase_single.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_vector_phase_single.restype = qelib_int

qelib.qe_spin_det_vector_phase_double.argtypes = [
        qelib_qe_spin_det_vector_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_vector_phase_double.restype = qelib_int

qelib.qe_spin_det_apply_xor.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        ]
qelib.qe_spin_det_apply_xor.restype = qelib_int

qelib.qe_spin_det_apply_and.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        ]
qelib.qe_spin_det_apply_and.restype = qelib_int

qelib.qe_spin_det_apply_or.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        qelib_qe_spin_det_generic_type, 
        ]
qelib.qe_spin_det_apply_or.restype = qelib_int

qelib.qe_spin_det_apply_popcount.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type
        ]
qelib.qe_spin_det_apply_popcount.restype = qelib_int

qelib.qe_spin_det_apply_single_excitation.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_apply_single_excitation.restype = qelib_int

qelib.qe_spin_det_apply_double_excitation.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_apply_double_excitation.restype = qelib_int

qelib.qe_spin_det_apply_exc_degree.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        ]

qelib.qe_spin_det_apply_exc_degree.restype = qelib_int

qelib.qe_spin_det_apply_get_holes.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        ]

qelib.qe_spin_det_apply_get_holes.restype = qelib_int

qelib.qe_spin_det_apply_get_particles.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        qelib_qe_spin_det_generic_type,
        ]

qelib.qe_spin_det_apply_get_particles.restype = qelib_int

qelib.qe_spin_det_apply_phase_single.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_apply_phase_single.restype = qelib_int

qelib.qe_spin_det_apply_phase_double.argtypes = [
        ctypes.c_int,
        qelib_qe_spin_det_generic_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        qelib_qe_orbital_int_type,
        ]
qelib.qe_spin_det_apply_phase_double.restype = qelib_int

