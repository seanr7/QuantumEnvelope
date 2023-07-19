#include <iostream>
#include <vector>
#include <tuple>
#include <array>
#include <string>
#include <bitset>

extern "C"{
    // Declare relevant types; int and tuple of ints
    typedef uint64_t sdet_t;

    sdet_t bitstring_XOR(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i ^ sdet_j;
    } 

    sdet_t bitstring_AND(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i & sdet_j;
    }

    sdet_t bitstring_OR(const sdet_t sdet_i, const sdet_t sdet_j){
        return sdet_i | sdet_j;
    }

    int bitstring_popcnt(const sdet_t sdet){
        std::bitset<64> bs_sdet(sdet);
        return bs_sdet.count();
    }

    // Q: How to do array? Need to intialize with size (Norb)? No.. Vectors?
    // typedef std::vector<int> sdet_vec_t;

    // TODO: This needs to be passed a pointer
    // sdet_t to_bitstring(const sdet_vec_t& sdet){
    //     // Declare bitset 
    //     std::bitset<64> bitstring;
    //     // Iterate through vector
    //     for(const int& orbital_idx : sdet){ /* Note; * gets reference from pointer */
    //         // Set appropriate bits to true
    //         bitstring.set(orbital_idx, true);
    //     }   
    //     // Return as sdet_t
    //     return bitstring.to_ullong();
    // }

    // // TODO: This needs to return a pointer
    // sdet_vec_t to_tuple(const sdet_t& sdet){
    //     // Declare bitset; convert integer spindet to bitset
    //     std::bitset<64> bitstring(sdet); 
    //     sdet_vec_t sdet_vec; 
    //     for (int i = 0; i < bitstring.size(); i++){
    //         if (bitstring[i] == 1) {
    //             sdet_vec.push_back(i);
    //         }
    //     }
    //     // Return pointer to vector object
    //     return sdet_vec;
    // }


    // sdet_t bitstring_XOR_withtup(const sdet_t& sdet_i, sdet_vec_t& sdet_vec_j){
    //     // Overloaded function; for case when input is a tuple
    //     // First, create a bitmask
    //     sdet_t sdet_j = to_bitstring(sdet_vec_j); 
    //     return sdet_i ^ sdet_j;
    // }

    struct ExcDegreeResult {
        int ed_up;
        int ed_dn;
    };

    // Helper function to calculate the popcnt (population count) of a 64-bit unsigned integer
    // int popcnt(uint64_t x) {
    //     return __builtin_popcountll(x);
    // }

    // Excitation degree function only for bit strings.
    ExcDegreeResult exc_degree(uint64_t alpha, uint64_t beta, uint64_t det_J_alpha, uint64_t det_J_beta) {
        ExcDegreeResult result;
        result.ed_up = bitstring_popcnt(bitstring_XOR(alpha, det_J_alpha)) / 2;
        result.ed_dn = bitstring_popcnt(bitstring_XOR(beta, det_J_beta)) / 2;
        return result;
    }
}

// int main() {
    // Do my function work?
    // sdet_vec_t sdet_vec = {0, 2, 3, 5};
    // // Want 0b101101;
    // sdet_t sdet_bs = to_bitstring(sdet_vec);
    // std::bitset<64>bitstring(sdet_bs);
    // std::cout << "Bitstring guy " << bitstring << std::endl;
    // // Other way
    // sdet_vec_t sdet_back_to_vec = to_tuple(sdet_bs);
    // for(const int& orbital_idx : sdet_back_to_vec){
    //     std::cout << "Vector guy " << orbital_idx << std::endl;
    // }

    // sdet_t sdet1 = 0b10111;
    // sdet_t sdet2 = 0b10111;

    // std::cout << "XOR result " << (sdet1 ^ sdet2) << std::endl;

    // return 0;

// }