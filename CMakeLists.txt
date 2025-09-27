cmake_minimum_required(VERSION 3.15)
project(zen5_optimizer VERSION 0.1.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler requirements
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(WARNING "This project is optimized for GCC. Current compiler: ${CMAKE_CXX_COMPILER_ID}")
endif()

# Set compiler flags for AMD Zen 5
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -fPIC -Wall -Wextra")

# Add Zen 5 specific optimizations if using GCC
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=znver5 -mtune=znver5")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffast-math -fno-finite-math-only")
endif()

# Create shared library
add_library(zen5_optimizer SHARED
    src/zen5_optimizer.cpp
    src/memory/hugepage_wrapper.cpp
)

# Include directories
target_include_directories(zen5_optimizer PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Link required libraries
target_link_libraries(zen5_optimizer PRIVATE
    dl      # For dlsym
)

# Set library properties
set_target_properties(zen5_optimizer PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    OUTPUT_NAME "zen5_optimizer"
)

# Installation rules (optional)
install(TARGETS zen5_optimizer
    LIBRARY DESTINATION lib
)

# Print configuration summary
message(STATUS "========================================")
message(STATUS "zen5_optimizer Configuration Summary")
message(STATUS "========================================")
message(STATUS "Version: ${PROJECT_VERSION}")
message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "========================================")