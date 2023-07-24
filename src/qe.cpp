#include "qe.h"

#include <array>
#include <assert.h>
#include <iostream>
#include <vector>
#include <tuple>
#include <string>
#include <bitset>
#include <stdlib.h>
#include <algorithm>

typedef std::vector<qe_orbital_int_t> qe_spin_det_vector_t;

void *qe_spin_det_vector_create()
{
	qe_spin_det_vector_t *ret = new std::vector<qe_orbital_int_t>;
	return (void *)ret;
}

void qe_spin_det_vector_destroy(qe_spin_det_vector_t *v)
{
	free(v);
}

int qe_spin_det_vector_xor(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_symmetric_difference(a->begin(), a->end(), b->begin(), b->end(),
				      std::back_inserter(*c));
	return 0;
}

int qe_spin_det_vector_and(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_intersection(a->begin(), a->end(), b->begin(), b->end(),
				      std::back_inserter(*c));
	return 0;
}


int qe_spin_det_vector_or(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_union(a->begin(), a->end(), b->begin(), b->end(),
				      std::back_inserter(*c));
	return 0;
}

size_t qe_spin_det_vector_popcount(qe_spin_det_vector_t *v)
{
	return v->size();
}

int qe_spin_det_vector_apply_excitation(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_union(a->begin(), a->end(), b->begin(), b->end(),
				      std::back_inserter(*c));
	return 0;
}

int qe_spin_det_vector_apply_single_excitation(qe_spin_det_vector_t *v,
					       qe_orbital_int_t hole,
					       qe_orbital_int_t particle)
{
	if (hole < particle) {
		size_t i = 0;
		/* find the hole */
		for (;i < v->size() && (*v)[i] < hole; i++);
		/* move the element until particle */
		for (; i < v->size() && (*v)[i] < particle; i++)
			v[i] = v[i+1];
		(*v)[i] = particle;
	}
	else {
		size_t i = v->size() - 1;
		/* find the hole */
		for (;i >= 0 && (*v)[i] > hole; i--);
		/* move the element until particle */
		for (; i >= 0 && (*v)[i] > particle; i--)
			v[i] = v[i-1];
		(*v)[i] = particle;
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

