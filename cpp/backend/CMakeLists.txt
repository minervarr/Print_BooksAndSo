# ---------------------------------------------------------------------------
# printbooks_backend — FreeType GlyphSource (and later qpdf emit/probe).
#
# This is the only tree allowed to link freetype / libqpdf. core/*_test
# executables must never list these sources; glyphs_freetype_test is the
# exception because it is proving the backend itself.
# ---------------------------------------------------------------------------
add_library(printbooks_backend STATIC
    freetype/glyphs_freetype.cc
)

target_include_directories(printbooks_backend PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(printbooks_backend PUBLIC cxx_std_17)
target_link_libraries(printbooks_backend PUBLIC printbooks_core PRIVATE freetype)

get_filename_component(_printbooks_font_dir
    "${CMAKE_SOURCE_DIR}/../assets/fonts" ABSOLUTE)
target_compile_definitions(printbooks_backend PUBLIC
    PRINTBOOKS_FONT_DIR="${_printbooks_font_dir}")

if(MSVC)
    target_compile_options(printbooks_backend PRIVATE /W3 /utf-8)
else()
    target_compile_options(printbooks_backend PRIVATE -Wall -Wextra)
endif()

if(PRINTBOOKS_TESTS)
    add_executable(glyphs_freetype_test tests/glyphs_freetype_test.cc)
    target_link_libraries(glyphs_freetype_test PRIVATE printbooks_backend)
    if(MSVC)
        target_compile_options(glyphs_freetype_test PRIVATE /W3 /utf-8)
    else()
        target_compile_options(glyphs_freetype_test PRIVATE -Wall -Wextra)
    endif()
    add_test(NAME glyphs_freetype_test COMMAND glyphs_freetype_test)
endif()
