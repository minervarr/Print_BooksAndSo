# ---------------------------------------------------------------------------
# printbooks_core — the portable half: units, geometry, the page-slot model, and
# the content-stream emitters.
#
# Zero OS headers, zero PDF library, zero font library, zero I/O. It parses,
# plans and decides — it never touches a PDF object and never opens a font file.
# The GlyphSource seam in metrics.hh is the ONLY door a font enters through, and
# it is an abstract interface; if this target's link line ever needs libqpdf or
# freetype, something leaked in.
# ---------------------------------------------------------------------------
add_library(printbooks_core STATIC
    src/units.cc
    src/geometry.cc
    src/pdfops.cc
    src/plan.cc
    src/drawing.cc
    src/text.cc
    src/numwords.cc
    src/render.cc
)

target_include_directories(printbooks_core PUBLIC include)
target_compile_features(printbooks_core PUBLIC cxx_std_17)

if(MSVC)
    target_compile_options(printbooks_core PRIVATE /W3 /utf-8)
else()
    target_compile_options(printbooks_core PRIVATE -Wall -Wextra)
endif()

# ── Tests ───────────────────────────────────────────────────────────────────
#
# Debug-only, assert-based, no framework: the house convention. Each test
# COMPILES the real sources it exercises and links nothing else — that property
# is worth protecting more than the assertions are, because it is what keeps a
# test from quietly starting to depend on a PDF library. Gated on the OPTION,
# not on CMAKE_BUILD_TYPE, so a Release build can still run the suite. The
# sources `#undef NDEBUG`, so the asserts survive optimisation.
if(PRINTBOOKS_TESTS)
    add_executable(units_test tests/units_test.cc src/units.cc)

    add_executable(geometry_test tests/geometry_test.cc
        src/geometry.cc src/units.cc)

    add_executable(plan_test tests/plan_test.cc src/plan.cc)

    add_executable(drawing_test tests/drawing_test.cc
        src/drawing.cc src/pdfops.cc src/geometry.cc src/units.cc)

    add_executable(text_test tests/text_test.cc
        src/text.cc src/pdfops.cc)

    add_executable(numwords_test tests/numwords_test.cc src/numwords.cc)

    add_executable(render_test tests/render_test.cc
        src/render.cc src/text.cc src/drawing.cc src/geometry.cc src/units.cc
        src/numwords.cc src/pdfops.cc src/plan.cc)

    foreach(_t units_test geometry_test plan_test drawing_test text_test
                numwords_test render_test)
        target_include_directories(${_t} PRIVATE include)
        if(MSVC)
            target_compile_options(${_t} PRIVATE /W3 /utf-8)
        else()
            target_compile_options(${_t} PRIVATE -Wall -Wextra)
        endif()
        add_test(NAME ${_t} COMMAND ${_t})
    endforeach()
endif()
