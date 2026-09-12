// numwords_test.cc — chapter numbers as English words.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <stdexcept>

#include "printbooks/numwords.hh"

using namespace pb;

static void test_numbers_become_words() {
    assert(ordinal_words(1) == "one");
    assert(ordinal_words(2) == "two");
    assert(ordinal_words(9) == "nine");
    assert(ordinal_words(10) == "ten");
    assert(ordinal_words(11) == "eleven");
    assert(ordinal_words(12) == "twelve");
    assert(ordinal_words(13) == "thirteen");
    assert(ordinal_words(15) == "fifteen");
    assert(ordinal_words(19) == "nineteen");
    assert(ordinal_words(20) == "twenty");
    assert(ordinal_words(21) == "twenty-one");
    assert(ordinal_words(30) == "thirty");
    assert(ordinal_words(42) == "forty-two");
    assert(ordinal_words(50) == "fifty");
    assert(ordinal_words(99) == "ninety-nine");
}

static void test_the_hyphen_is_a_hyphen_not_a_space() {
    const std::string s = ordinal_words(21);
    assert(s.find('-') != std::string::npos);
    assert(s.find(' ') == std::string::npos);
}

static void test_zero_and_negatives_are_rejected() {
    bool threw_zero = false, threw_neg = false;
    try {
        ordinal_words(0);
    } catch (const std::invalid_argument&) {
        threw_zero = true;
    }
    try {
        ordinal_words(-3);
    } catch (const std::invalid_argument&) {
        threw_neg = true;
    }
    assert(threw_zero && threw_neg);
}

static void test_beyond_the_table_it_says_so_rather_than_guessing() {
    assert(ordinal_words(100) == "100");
    assert(ordinal_words(137) == "137");
}

int main() {
    test_numbers_become_words();
    test_the_hyphen_is_a_hyphen_not_a_space();
    test_zero_and_negatives_are_rejected();
    test_beyond_the_table_it_says_so_rather_than_guessing();
    std::printf("numwords_test: all assertions passed\n");
    return 0;
}
