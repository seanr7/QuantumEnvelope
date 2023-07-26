
#include <array>
#include <assert.h>
#include <iostream>
#include <vector>
#include <tuple>
#include <string>
#include <bitset>
#include <stdlib.h>
#include <algorithm>

#include "qe.h"

struct qe_spin_det_vector_s {
	std::vector<qe_orbital_int_t> v;
};

void *qe_spin_det_vector_create(qe_orbital_int_t *array, size_t length)
{
	qe_spin_det_vector_t *ret = new qe_spin_det_vector_t;
	ret->v.insert(ret->v.end(), array, array + length);
	return (void *)ret;
}

void qe_spin_det_vector_destroy(qe_spin_det_vector_t *v)
{
	delete v;
}

int qe_spin_det_vector_xor(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_symmetric_difference(a->v.begin(), a->v.end(), b->v.begin(), b->v.end(),
				      std::back_inserter(c->v));
	return 0;
}

int qe_spin_det_vector_and(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_intersection(a->v.begin(), a->v.end(), b->v.begin(), b->v.end(),
				      std::back_inserter(c->v));
	return 0;
}


int qe_spin_det_vector_or(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_union(a->v.begin(), a->v.end(), b->v.begin(), b->v.end(),
				      std::back_inserter(c->v));
	return 0;
}

size_t qe_spin_det_vector_popcount(qe_spin_det_vector_t *v)
{
	return v->v.size();
}

int qe_spin_det_vector_apply_single_excitation(qe_spin_det_vector_t *v,
					       qe_orbital_int_t hole,
					       qe_orbital_int_t particle)
{
	if (hole < particle) {
		size_t i = 0;
		/* find the hole */
		for (;i < v->v.size() && v->v[i] < hole; i++);
		/* move the element until particle */
		for (; i < v->v.size() && v->v[i] < particle; i++)
			v[i] = v[i+1];
		v->v[i] = particle;
	}
	else {
		size_t i = v->v.size() - 1;
		/* find the hole */
		for (;i >= 0 && v->v[i] > hole; i--);
		/* move the element until particle */
		for (; i >= 0 && v->v[i] > particle; i--)
			v[i] = v[i-1];
		v->v[i] = particle;
	}
	return 0;	
}

int qe_spin_det_vector_apply_double_excitation(qe_spin_det_vector_t *v,
					       qe_orbital_int_t h1,
					       qe_orbital_int_t p1,
					       qe_orbital_int_t h2,
					       qe_orbital_int_t p2)
{
	qe_spin_det_vector_apply_single_excitation(v, h1, p1);
	qe_spin_det_vector_apply_single_excitation(v, h2, p2);
	return 0;
}

int qe_spin_det_apply_xor(int type, void *a, void *b, void *c)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_xor((qe_spin_det_vector_t *)a,
					      (qe_spin_det_vector_t *)b,
					      (qe_spin_det_vector_t *)c);
	}
	return -EINVAL;
}

int qe_spin_det_apply_or(int type, void *a, void *b, void *c)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_or((qe_spin_det_vector_t *)a,
					      (qe_spin_det_vector_t *)b,
					      (qe_spin_det_vector_t *)c);
	}
	return -EINVAL;
}
int qe_spin_det_apply_and(int type, void *a, void *b, void *c)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_and((qe_spin_det_vector_t *)a,
					      (qe_spin_det_vector_t *)b,
					      (qe_spin_det_vector_t *)c);
	}
	return -EINVAL;
}
int qe_spin_det_apply_popcount(int type, void *a)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_popcount((qe_spin_det_vector_t *)a);
	}
	return -EINVAL;
}

int qe_spin_det_apply_single_excitation(int type, void *a, qe_orbital_int_t h,
					qe_orbital_int_t p)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_apply_single_excitation((qe_spin_det_vector_t *)a,
					      (qe_orbital_int_t)h,
					      (qe_orbital_int_t)p);
	}
	return -EINVAL;
}

int qe_spin_det_apply_double_excitation(int type, void *a, qe_orbital_int_t h,
					qe_orbital_int_t p,
					qe_orbital_int_t h2,
					qe_orbital_int_t p2)
{
	if (type == SPIN_DET_TYPE_VECTOR) {
		return qe_spin_det_vector_apply_double_excitation((qe_spin_det_vector_t *)a,
					      (qe_orbital_int_t)h,
					      (qe_orbital_int_t)p,
					      (qe_orbital_int_t)h2,
					      (qe_orbital_int_t)p2
					      );
	}
	return -EINVAL;
}
