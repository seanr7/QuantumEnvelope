
#ifndef QE_HEADER_H
#define QE_HEADER_H 1

extern "C" {

#include <stdlib.h>
#include <stdint.h>

typedef uint32_t qe_orbital_int_t;
typedef struct qe_spin_det_vector_s qe_spin_det_vector_t;

void *qe_spin_det_vector_create(qe_orbital_int_t *array, size_t length);
void qe_spin_det_vector_destroy(qe_spin_det_vector_t *v);
int qe_spin_det_vector_xor(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c);
int qe_spin_det_vector_and(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c);
int qe_spin_det_vector_or(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c);
size_t qe_spin_det_vector_popcount(qe_spin_det_vector_t *v);
int qe_spin_det_vector_apply_single_excitation(qe_spin_det_vector_t *v,
					       qe_orbital_int_t hole,
					       qe_orbital_int_t particle);
int qe_spin_det_vector_apply_double_excitation(qe_spin_det_vector_t *v,
					       qe_orbital_int_t h1,
					       qe_orbital_int_t p1,
					       qe_orbital_int_t h2,
					       qe_orbital_int_t p2);

}

#define SPIN_DET_TYPE_VECTOR 0
#define SPIN_DET_TYPE_MAX 1

int qe_spin_det_apply_xor(int type, void *, void *, void *);
int qe_spin_det_apply_and(int type, void *, void *, void *);
int qe_spin_det_apply_or(int type, void *, void *, void *);
int qe_spin_det_apply_popcount(int type, void *);
int qe_spin_det_apply_single_excitation(int type, void *, qe_orbital_int_t, qe_orbital_int_t);
int qe_spin_det_apply_double_excitation(int type, void *, qe_orbital_int_t, qe_orbital_int_t, qe_orbital_int_t, qe_orbital_int_t);

#endif
