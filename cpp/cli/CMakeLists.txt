# ---------------------------------------------------------------------------
# printbooks_cli — print-books init + build.
#
# Links printbooks_backend (PUBLIC core; qpdf/freetype private). OUTPUT_NAME
# so the binary is build/.../cli/print-books, matching the Python entry point.
# ---------------------------------------------------------------------------
add_executable(printbooks_cli cli_main.cc)
target_link_libraries(printbooks_cli PRIVATE printbooks_backend)
set_target_properties(printbooks_cli PROPERTIES OUTPUT_NAME print-books)
target_compile_features(printbooks_cli PUBLIC cxx_std_17)

if(MSVC)
    target_compile_options(printbooks_cli PRIVATE /W3 /utf-8)
else()
    target_compile_options(printbooks_cli PRIVATE -Wall -Wextra)
endif()

if(PRINTBOOKS_TESTS)
    add_executable(cli_paths_test tests/paths_test.cc)
    target_include_directories(cli_paths_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    target_compile_features(cli_paths_test PRIVATE cxx_std_17)
    if(MSVC)
        target_compile_options(cli_paths_test PRIVATE /W3 /utf-8)
    else()
        target_compile_options(cli_paths_test PRIVATE -Wall -Wextra)
    endif()
    add_test(NAME cli_paths_test COMMAND cli_paths_test)
endif()
