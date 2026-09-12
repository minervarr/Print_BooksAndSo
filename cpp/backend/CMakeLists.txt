# ---------------------------------------------------------------------------
# printbooks_backend — FreeType GlyphSource, qpdf probe, project TOML.
#
# This is the only tree allowed to link freetype / libqpdf. core/*_test
# executables must never list these sources; the backend tests are the
# exception because they are proving the backend itself.
# ---------------------------------------------------------------------------
add_library(printbooks_backend STATIC
    freetype/glyphs_freetype.cc
    qpdf/pdf_qpdf.cc
    project.cc
)

target_include_directories(printbooks_backend PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(printbooks_backend PUBLIC cxx_std_17)
target_link_libraries(printbooks_backend
    PUBLIC printbooks_core
    PRIVATE freetype libqpdf tomlplusplus::tomlplusplus)

get_filename_component(_printbooks_font_dir
    "${CMAKE_SOURCE_DIR}/../assets/fonts" ABSOLUTE)
get_filename_component(_printbooks_fixture_dir
    "${CMAKE_SOURCE_DIR}/../fixtures" ABSOLUTE)
target_compile_definitions(printbooks_backend PUBLIC
    PRINTBOOKS_FONT_DIR="${_printbooks_font_dir}")

if(MSVC)
    target_compile_options(printbooks_backend PRIVATE /W3 /utf-8)
else()
    target_compile_options(printbooks_backend PRIVATE -Wall -Wextra)
endif()

if(PRINTBOOKS_TESTS)
    add_executable(glyphs_freetype_test tests/glyphs_freetype_test.cc)
    add_executable(pdf_qpdf_test tests/pdf_qpdf_test.cc)
    target_link_libraries(glyphs_freetype_test PRIVATE printbooks_backend)
    target_link_libraries(pdf_qpdf_test PRIVATE printbooks_backend libqpdf)
    target_compile_definitions(pdf_qpdf_test PRIVATE
        PRINTBOOKS_FIXTURE_DIR="${_printbooks_fixture_dir}")
    if(MSVC)
        target_compile_options(glyphs_freetype_test PRIVATE /W3 /utf-8)
        target_compile_options(pdf_qpdf_test PRIVATE /W3 /utf-8)
    else()
        target_compile_options(glyphs_freetype_test PRIVATE -Wall -Wextra)
        target_compile_options(pdf_qpdf_test PRIVATE -Wall -Wextra)
    endif()
    add_test(NAME glyphs_freetype_test COMMAND glyphs_freetype_test)
    add_test(NAME pdf_qpdf_test COMMAND pdf_qpdf_test)
endif()
