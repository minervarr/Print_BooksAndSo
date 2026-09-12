// numwords.cc — chapter numbers as English words.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.

#include "printbooks/numwords.hh"

#include <stdexcept>

namespace pb {

namespace {

const char* const kOnes[] = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
};

const char* const kTens[] = {
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
};

}  // namespace

std::string ordinal_words(int number) {
    if (number < 1)
        throw std::invalid_argument("chapters are 1-based");

    if (number < 20)
        return kOnes[number];
    if (number < 100) {
        const int tens = number / 10;
        const int ones = number % 10;
        if (ones == 0)
            return kTens[tens];
        return std::string(kTens[tens]) + "-" + kOnes[ones];
    }
    return std::to_string(number);
}

}  // namespace pb
