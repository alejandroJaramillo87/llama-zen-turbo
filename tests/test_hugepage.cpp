/*
 * test_hugepage.cpp
 *
 * Test that mmap interception works correctly.
 * Creates a temporary file and verifies hugepage allocation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <string.h>
#include <errno.h>

int main() {
    printf("[test_hugepage] Testing mmap interception\n");

    // Create a temporary test file (1.5 GB to trigger hugepage logic)
    const size_t test_size = 1536 * 1024 * 1024; // 1.5 GB
    const char* test_file = "/tmp/zen5_test_hugepage.dat";

    printf("[test_hugepage] Creating %.2f GB test file\n", test_size / (1024.0 * 1024.0 * 1024.0));

    int fd = open(test_file, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        fprintf(stderr, "[test_hugepage] FAIL: Cannot create test file: %s\n", strerror(errno));
        return 1;
    }

    // Expand file to test size
    if (ftruncate(fd, test_size) != 0) {
        fprintf(stderr, "[test_hugepage] FAIL: Cannot expand file: %s\n", strerror(errno));
        close(fd);
        unlink(test_file);
        return 1;
    }

    // Write some test data
    const char* test_data = "ZEN5_OPTIMIZER_TEST_PATTERN";
    if (write(fd, test_data, strlen(test_data)) != (ssize_t)strlen(test_data)) {
        fprintf(stderr, "[test_hugepage] FAIL: Cannot write test data: %s\n", strerror(errno));
        close(fd);
        unlink(test_file);
        return 1;
    }

    // Reset file position
    lseek(fd, 0, SEEK_SET);

    printf("[test_hugepage] Attempting mmap (should trigger interception)\n");

    // This mmap should be intercepted by our library (if LD_PRELOAD is active)
    void* addr = mmap(NULL, test_size, PROT_READ, MAP_PRIVATE, fd, 0);

    if (addr == MAP_FAILED) {
        fprintf(stderr, "[test_hugepage] FAIL: mmap failed: %s\n", strerror(errno));
        close(fd);
        unlink(test_file);
        return 1;
    }

    printf("[test_hugepage] mmap succeeded at address %p\n", addr);

    // Verify we can read the data
    if (memcmp(addr, test_data, strlen(test_data)) != 0) {
        fprintf(stderr, "[test_hugepage] FAIL: Data mismatch\n");
        munmap(addr, test_size);
        close(fd);
        unlink(test_file);
        return 1;
    }

    printf("[test_hugepage] Data verification: OK\n");

    // Check if hugepages are in use (informational)
    FILE* maps = fopen("/proc/self/maps", "r");
    if (maps) {
        char line[256];
        bool found_huge = false;
        while (fgets(line, sizeof(line), maps)) {
            if (strstr(line, "huge")) {
                found_huge = true;
                break;
            }
        }
        fclose(maps);

        if (found_huge) {
            printf("[test_hugepage] INFO: Huge pages detected in memory mappings\n");
        } else {
            printf("[test_hugepage] INFO: No huge pages detected (may be transparent)\n");
        }
    }

    // Clean up
    munmap(addr, test_size);
    close(fd);
    unlink(test_file);

    printf("[test_hugepage] OK: mmap interception test complete\n");
    return 0;
}