
#include <array>
#include <assert.h>
#include <iostream>
#include <vector>
#include <tuple>
#include <string>
#include <bitset>
#include <stdlib.h>
#include <algorithm>

#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "include/doctest/doctest.h"

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

TEST_CASE("Testing the `qe_spin_det_vector_xor` function")
{
    /* Some overlap */
    qe_spin_det_vector_t a {{0, 1}};
    qe_spin_det_vector_t b {{0, 2}};
    qe_spin_det_vector_t res;
    qe_spin_det_vector_xor(&a, &b, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {1, 2});

    /* All overlap */
    res.v.clear();
    qe_spin_det_vector_t a_copy;
    a_copy = a;
    /* Should be empty */
    qe_spin_det_vector_xor(&a, &a_copy, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {});

    /* No overlap */
    res.v.clear();
    qe_spin_det_vector_t c {{2, 3}};
    qe_spin_det_vector_xor(&a, &c, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {0, 1, 2, 3});
}

int qe_spin_det_vector_and(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_intersection(a->v.begin(), a->v.end(), b->v.begin(), b->v.end(),
				      std::back_inserter(c->v));
	return 0;
}

TEST_CASE("Testing the `qe_spin_det_vector_and` function")
{   
    /* Some overlap */
    qe_spin_det_vector_t a {{0, 1}};
    qe_spin_det_vector_t b {{0, 2}};
    qe_spin_det_vector_t res;
    qe_spin_det_vector_and(&a, &b, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {0});

    /* All overlap */
    res.v.clear();
    qe_spin_det_vector_t a_copy;
    a_copy = a;
    qe_spin_det_vector_and(&a, &a_copy, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {0, 1});

    /* No overlap */
    res.v.clear();
    qe_spin_det_vector_t c {{2, 3}};
    /* Should be empty */
    qe_spin_det_vector_and(&a, &c, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {});
}

int qe_spin_det_vector_or(qe_spin_det_vector_t *a, qe_spin_det_vector_t *b,
			   qe_spin_det_vector_t *c)
{
        std::set_union(a->v.begin(), a->v.end(), b->v.begin(), b->v.end(),
				      std::back_inserter(c->v));
	return 0;
}

TEST_CASE("Testing the `qe_spin_det_vector_or` function")
{   
    /* Some overlap */
    qe_spin_det_vector_t a {{0, 1}};
    qe_spin_det_vector_t b {{0, 2}};
    qe_spin_det_vector_t res;
    qe_spin_det_vector_or(&a, &b, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t> {0, 1, 2});

    /* All overlap */
    res.v.clear();
    qe_spin_det_vector_t a_copy;
    a_copy = a;
    qe_spin_det_vector_or(&a, &a_copy, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t>  {0, 1});

    /* No overlap */
    res.v.clear();
    qe_spin_det_vector_t c {{2, 3}};
    /* Should be empty */
    qe_spin_det_vector_or(&a, &c, &res);
    CHECK(res.v == std::vector<qe_orbital_int_t>  {0, 1, 2, 3});
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
		for (; i < v->v.size() - 1 && v->v[i] < particle; i++)
			v->v[i] = v->v[i+1];
		if (particle < v->v[i]) { 
            v->v[i-1] = particle;
        } else { 
            v->v[i] = particle;
        }
	}
	else {
		size_t i = v->v.size() - 1;
		/* find the hole */
		for (;i >= 0 && v->v[i] > hole; i--);
		/* move the element until particle */
		for (; i >= 0 && v->v[i] > particle; i--)
			v->v[i] = v->v[i-1];
		if (particle < v->v[i]) { 
            v->v[i] = particle;
        } else {
            v->v[i+1] = particle;
        }
	}
	return 0;	
}

TEST_CASE("Testing the `qe_spin_det_vector_apply_single_excitation` function")
{   
    SUBCASE("hole < particle"){
        /* hole, particle adjacent at start */
        qe_spin_det_vector_t a {{0, 2, 3, 6, 7, 8}};
        qe_spin_det_vector_apply_single_excitation(&a, 0, 1);
        CHECK(a.v == std::vector<qe_orbital_int_t> {1, 2, 3, 6, 7, 8});

        /* hole, particle adjacent at end */
        qe_spin_det_vector_apply_single_excitation(&a, 8, 9);
        CHECK(a.v == std::vector<qe_orbital_int_t>  {1, 2, 3, 6, 7, 9});

        /* hole, particle adjacent in middle */
        qe_spin_det_vector_apply_single_excitation(&a, 3, 4);
        CHECK(a.v == std::vector<qe_orbital_int_t>  {1, 2, 4, 6, 7, 9});

        /* hole, particle not adjacent */   
        qe_spin_det_vector_apply_single_excitation(&a, 2, 8);
        CHECK(a.v == std::vector<qe_orbital_int_t> {1, 4, 6, 7, 8, 9});
    }

    SUBCASE("particle < hole"){
        qe_spin_det_vector_t a {{0, 2, 3, 6, 7, 9}};
        /* hole, particle adjacent at start */
        qe_spin_det_vector_apply_single_excitation(&a, 2, 1);
        CHECK(a.v == std::vector<qe_orbital_int_t> {0, 1, 3, 6, 7, 9});

        /* hole, particle adjacent at end */
        qe_spin_det_vector_apply_single_excitation(&a, 9, 8);
        CHECK(a.v == std::vector<qe_orbital_int_t> {0, 1, 3, 6, 7, 8});

        /* hole, particle adjacent in middle */
        qe_spin_det_vector_apply_single_excitation(&a, 6, 5);
        CHECK(a.v == std::vector<qe_orbital_int_t> {0, 1, 3, 5, 7, 8});

        /* hole, particle not adjacent */   
        qe_spin_det_vector_apply_single_excitation(&a, 7, 2);
        CHECK(a.v == std::vector<qe_orbital_int_t> {0, 1, 2, 3, 5, 8});
    }
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

TEST_CASE("Testing the `qe_spin_det_vector_apply_double_excitation` function")
{   
    qe_spin_det_vector_t a {{0, 1, 2, 3}};
    qe_spin_det_vector_apply_double_excitation(&a, 2, 4, 3, 5);
    CHECK(a.v == std::vector<qe_orbital_int_t> {0, 1, 4, 5});

    qe_spin_det_vector_apply_double_excitation(&a, 1, 2, 5, 6);
    CHECK(a.v == std::vector<qe_orbital_int_t>{0, 2, 4, 6});
}

// Generic handles

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
