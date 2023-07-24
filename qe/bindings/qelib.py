import ctypes

qelib = ctypes.find_library("../../src/qe.so")

qelib_qe_orbital_int_type = ctypes.c_uint32
qelib_qe_spin_det_vector_type = ctypes.c_void_p
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

