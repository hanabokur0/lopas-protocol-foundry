cmake_minimum_required(VERSION 3.20)
project(lopas_protocol_foundry_cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(LOPAS_ENABLE_SANITIZERS "Enable ASan/UBSan on GCC/Clang" OFF)

find_path(JSONC_INCLUDE_DIR json-c/json.h REQUIRED)
find_library(JSONC_LIBRARY json-c REQUIRED)

add_library(lopas_foundry
    src/types.cpp
    src/expression.cpp
    src/foundry.cpp
    src/io.cpp
)

target_include_directories(lopas_foundry
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE ${JSONC_INCLUDE_DIR}
)
target_link_libraries(lopas_foundry PRIVATE ${JSONC_LIBRARY})

target_compile_options(lopas_foundry PRIVATE -Wall -Wextra -Wpedantic)

if(LOPAS_ENABLE_SANITIZERS AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(lopas_foundry PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(lopas_foundry PRIVATE -fsanitize=address,undefined)
endif()

add_executable(lopas_foundry_cli src/main.cpp)
target_link_libraries(lopas_foundry_cli PRIVATE lopas_foundry ${JSONC_LIBRARY})
set_target_properties(lopas_foundry_cli PROPERTIES OUTPUT_NAME lopas_foundry)

include(CTest)
if(BUILD_TESTING)
    add_executable(lopas_foundry_tests tests/test_main.cpp)
    target_link_libraries(lopas_foundry_tests PRIVATE lopas_foundry ${JSONC_LIBRARY})
    add_test(NAME lopas_foundry_tests COMMAND lopas_foundry_tests)
endif()
