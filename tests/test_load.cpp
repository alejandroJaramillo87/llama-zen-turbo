/*
 * test_load.cpp
 *
 * Test that the zen5_optimizer library loads correctly.
 */

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("[test_load] Attempting to load libzen5_optimizer.so\n");

    // Try to load the library
    void* handle = dlopen("./build/libzen5_optimizer.so", RTLD_NOW);

    if (!handle) {
        fprintf(stderr, "[test_load] FAIL: %s\n", dlerror());
        return 1;
    }

    printf("[test_load] OK: Library loaded successfully\n");

    // Clean up
    dlclose(handle);

    return 0;
}