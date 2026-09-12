// numwords.hh — chapter numbers as English words, for the portrait kicker.
//
// Copyright (C) 2026 nava. AGPLv3 or later; see LICENSE.
//
// CHAPTER ONE rather than CHAPTER 1. A table, not an algorithm: offline,
// deterministic, no locale database, and the same twenty lines port unchanged.
#pragma once

#include <string>

namespace pb {

// `number` in lowercase English words, or the numeral past 99. Hyphenated,
// never spaced: "twenty one" would letterspace as two words on the portrait.
// Throws for a number below 1 (chapters are 1-based).
std::string ordinal_words(int number);

}  // namespace pb
