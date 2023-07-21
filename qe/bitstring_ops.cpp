#include <iostream>
#include <vector>
#include <tuple>
#include <array>
#include <string>
#include <bitset>
#include <stdlib.h>
#include <algorithm>    // std::set_intersection, std::sort
// In hpp header 
// extern "C"{
//     void  bitstring_XOR(const sdet_t sdet_i, const sdet_t sdet_j)
// }
extern "C"{
    // Declare relevant types; 64-bit int for bitstring representation of determinants
    typedef uint64_t sdet_t;
    // Vector of integers for `Tuple' representation
    typedef std::vector<int> sdet_vec_t;

    sdet_t bitstring_XOR(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i ^ sdet_j;
    } 

    sdet_t bitstring_AND(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i & sdet_j;
    }

    sdet_t bitstring_OR(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i | sdet_j;
    }

    int bitstring_POPCNT(const sdet_t sdet){
        std::bitset<64> bs_sdet(sdet);
        return bs_sdet.count();
    }

    void vec_AND(const int* sdet_i_ptr, const size_t size_i, const int* sdet_j_ptr, const size_t size_j, int* size_res_ptr, int** p){
        /* Inputs:
        :param sdet_i_ptr, size_i: pointer to first element of sdet_i (NumPy array in Python) and size of sdet_i
        :param sdet_j_ptr, size_j: "                         " sdet_j "                                 " sdet_j
        :param size_ptr          : pointer to address in memory where size of result will be stored

        */
        
        // Declare result
        sdet_vec_t AND_res;
        // For this function; vectors are assumed to be sorted. This is fine, since our spindets will always be sorted 
        std::set_intersection(sdet_i_ptr, sdet_i_ptr + size_i, sdet_j_ptr, sdet_j_ptr + size_j, std::back_inserter(AND_res));
        
        // How big is my result? Compute size_t, and set the passed size_res_ptr to point to the memory address of size_res
        int size_res = AND_res.size();
        // Copy at size_res_ptr, size_ptr
        *size_res_ptr = size_res; 
        
        // Get pointer to the data contained in the result...
        // malloc allocates size_res * sizeof(int) bytes, and read me the address at (the start of) this contiguous slab of memory
        int *result_ptr = (int *) malloc(size_res * sizeof(int));

        for (int i = 0; i < size_res; i++){
            // result_ptr[i] = &(result_ptr[0] + i * size(*result_ptr[0]))
            result_ptr[i] = AND_res[i];
        }
        // Or, *p = &result_ptr[0] 
        *p = result_ptr;
        // Outside the function now... 
    }

    void vec_XOR(const int* sdet_i_ptr, const size_t size_i, const int* sdet_j_ptr, const size_t size_j, int* size_res_ptr, int** p){
        /* Inputs:
        :param sdet_i_ptr, size_i: pointer to first element of sdet_i (NumPy array in Python) and size of sdet_i
        :param sdet_j_ptr, size_j: "                         " sdet_j "                                 " sdet_j
        :param size_ptr          : pointer to address in memory where size of result will be stored

        */
        
        // Declare result
        sdet_vec_t XOR_res;
        // For this function; vectors are assumed to be sorted. This is fine, since our spindets will always be sorted 
        std::set_symmetric_difference(sdet_i_ptr, sdet_i_ptr + size_i, sdet_j_ptr, sdet_j_ptr + size_j, std::back_inserter(XOR_res));
        
        // How big is my result? Compute size_t, and set the passed size_res_ptr to point to the memory address of size_res
        int size_res = XOR_res.size();
        // Copy at size_res_ptr, size_ptr
        *size_res_ptr = size_res; 
        
        // Get pointer to the data contained in the result...
        // malloc allocates size_res * sizeof(int) bytes, and read me the address at (the start of) this contiguous slab of memory
        int *result_ptr = (int *) malloc(size_res * sizeof(int));

        for (int i = 0; i < size_res; i++){
            // result_ptr[i] = &(result_ptr[0] + i * size(*result_ptr[0]))
            result_ptr[i] = XOR_res[i];
        }
        // Or, *p = &result_ptr[0] 
        *p = result_ptr;
        // Outside the function now... 
    }

    void vec_OR(const int* sdet_i_ptr, const size_t size_i, const int* sdet_j_ptr, const size_t size_j, int* size_res_ptr, int** p){
        /* Inputs:
        :param sdet_i_ptr, size_i: pointer to first element of sdet_i (NumPy array in Python) and size of sdet_i
        :param sdet_j_ptr, size_j: "                         " sdet_j "                                 " sdet_j
        :param size_ptr          : pointer to address in memory where size of result will be stored

        */
        
        // Declare result
        sdet_vec_t OR_res;
        // For this function; vectors are assumed to be sorted. This is fine, since our spindets will always be sorted 
        std::set_union(sdet_i_ptr, sdet_i_ptr + size_i, sdet_j_ptr, sdet_j_ptr + size_j, std::back_inserter(OR_res));
        
        // How big is my result? Compute size_t, and set the passed size_res_ptr to point to the memory address of size_res
        int size_res = OR_res.size();
        // Copy at size_res_ptr, size_ptr
        *size_res_ptr = size_res; 
        
        // Get pointer to the data contained in the result...
        // malloc allocates size_res * sizeof(int) bytes, and read me the address at (the start of) this contiguous slab of memory
        int *result_ptr = (int *) malloc(size_res * sizeof(int));

        for (int i = 0; i < size_res; i++){
            // result_ptr[i] = &(result_ptr[0] + i * size(*result_ptr[0]))
            result_ptr[i] = OR_res[i];
        }
        // Or, *p = &result_ptr[0] 
        *p = result_ptr;
        // Outside the function now... 
    }

    void apply_excitation_tuple(const int* self, const size_t size_self, const int* lh, const size_t size_lh, 
                                const int* lp, const size_t size_lp, int* size_res_ptr, int** p) {
        /* Inputs:
        self, size_self, pointer to numpy array and size of the array
        lh, size_lh, pointer to numpy array and size of the array
        lp, size_lp, pointer to numpy array and size of the array
        :param size_ptr          : pointer to address in memory where size of result will be stored
        */

        // Declare result
        sdet_vec_t OR_res, XOR_res;
        // For this function; vectors are assumed to be sorted. This is fine, since our spindets will always be sorted 
        // operations needed for apply_excitation
        std::set_union(lh, lh + size_lh, lp, lp + size_lp, std::back_inserter(OR_res));
        std::set_symmetric_difference(self, self + size_self, OR_res.begin(), OR_res.end(), std::back_inserter(XOR_res));
        // How big is my result? Compute size_t, and set the passed size_res_ptr to point to the memory address of size_res
        int size_res = XOR_res.size();
        // Copy at size_res_ptr, size_ptr
        *size_res_ptr = size_res; 
        
        // Get pointer to the data contained in the result...
        // malloc allocates size_res * sizeof(int) bytes, and read me the address at (the start of) this contiguous slab of memory
        int *result_ptr = (int *) malloc(size_res * sizeof(int));

        for (int i = 0; i < size_res; i++){
            // result_ptr[i] = &(result_ptr[0] + i * size(*result_ptr[0]))
            result_ptr[i] = XOR_res[i];
        }
        // Or, *p = &result_ptr[0] 
        *p = result_ptr;
        // Outside the function now... 
    }

    struct ExcDegreeResult {
        int ed_up;
        int ed_dn;
    };

    // Excitation degree function only for bit strings.
    ExcDegreeResult exc_degree_bitstring(sdet_t det_I_alpha, sdet_t det_I_beta, sdet_t det_J_alpha, sdet_t det_J_beta) {
        ExcDegreeResult result;
        result.ed_up = bitstring_POPCNT(bitstring_XOR(det_I_alpha, det_J_alpha)) / 2;
        result.ed_dn = bitstring_POPCNT(bitstring_XOR(det_I_beta, det_J_beta)) / 2;
        return result;
    }

    // Excitation degree function for vectors.
    int exc_degree_tuple(const int* det_I, const sdet_t size_det_I, const int* det_J, const sdet_t size_det_J){
    /* Inputs:
        :param det_I, size_det_I:  Pointer to tuple in python with determinant and the size of the tuple
        :param sdet_j_ptr, size_j: Pointer to tuple in python with determinant and the size of the tuple
        :param size_ptr          : pointer to address in memory where size of result will be stored
    */

    // define the vectors the set symmetric difference will do into
    sdet_vec_t XOR_res;

    // take the symmetric difference of both alpha and beta electrons 
    std::set_symmetric_difference(det_I, det_I + size_det_I, det_J, det_J + size_det_J, std::back_inserter(XOR_res));
    // divide the size by 2 because they come in pairs of 2
    int result = XOR_res.size() / 2;

    return result;
    }
}


// int main(){

//     // Test spin_determinants
//     sdet_vec_t sdet_i {0, 1, 8};
//     sdet_vec_t sdet_j {0, 8, 17};
//     sdet_vec_t AND_res;

//     // Declare pointer to size_t
//     int size_ptr;
//     // Pointer1 to Pointer2; Pointer2 is where in memory start of result is stored
//     int* res_ptr;
//     // Take their logical intersection
//     vec_AND(sdet_i.data(), 3, sdet_j.data(), 3, &size_ptr, &res_ptr);

//     // Now... Does it work?
//     std::cout << "Size of result " << size_ptr << std::endl;

//     for (int i = 0; i < size_ptr; i++){
//         std::cout << "Elements of intersection " << res_ptr[i] << std::endl;
//     }

//     return 0;
// }