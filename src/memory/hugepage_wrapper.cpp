/*
 * hugepage_wrapper.cpp
 *
 * Intercepts mmap() calls to provide transparent huge page support.
 * Allocates anonymous huge page memory for large file mappings
 * to reduce TLB pressure during model inference.
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#include "../config.h"

namespace zen5_turbo {

// Function pointer to the real mmap
typedef void* (*mmap_fn)(void*, size_t, int, int, int, off_t);
static mmap_fn real_mmap = nullptr;

// Function pointer to the real munmap
typedef int (*munmap_fn)(void*, size_t);
static munmap_fn real_munmap = nullptr;

// Track our anonymous huge page allocations
struct HugePageAllocation {
    void* addr;
    size_t size;
    HugePageAllocation* next;
};
static HugePageAllocation* allocations = nullptr;

// Initialize function pointers to real functions
static void init_functions() {
    if (!real_mmap) {
        real_mmap = (mmap_fn)dlsym(RTLD_NEXT, "mmap");
        if (!real_mmap) {
            fprintf(stderr, "[%s] ERROR: Failed to find real mmap: %s\n",
                    ZEN5_OPTIMIZER_NAME, dlerror());
            exit(1);
        }
    }
    if (!real_munmap) {
        real_munmap = (munmap_fn)dlsym(RTLD_NEXT, "munmap");
        if (!real_munmap) {
            fprintf(stderr, "[%s] ERROR: Failed to find real munmap: %s\n",
                    ZEN5_OPTIMIZER_NAME, dlerror());
            exit(1);
        }
    }
}

// Check if we should use huge pages for this file
static bool should_use_hugepages(int fd, size_t length) {
#if ENABLE_HUGEPAGES
    return length >= MIN_SIZE_FOR_HUGEPAGES;
#else
    return false;
#endif
}

// Track an allocation so we can handle munmap properly
static void track_allocation(void* addr, size_t size) {
    HugePageAllocation* alloc = (HugePageAllocation*)malloc(sizeof(HugePageAllocation));
    alloc->addr = addr;
    alloc->size = size;
    alloc->next = allocations;
    allocations = alloc;
}

// Find and remove a tracked allocation
static size_t untrack_allocation(void* addr) {
    HugePageAllocation** prev = &allocations;
    HugePageAllocation* curr = allocations;

    while (curr) {
        if (curr->addr == addr) {
            size_t size = curr->size;
            *prev = curr->next;
            free(curr);
            return size;
        }
        prev = &curr->next;
        curr = curr->next;
    }
    return 0;
}

// Cleanup function to be called on library unload
void cleanup_hugepage_allocations() {
    while (allocations) {
        HugePageAllocation* next = allocations->next;
        free(allocations);
        allocations = next;
    }
}

} // namespace zen5_turbo

// Our intercepted mmap function - must be extern "C" for LD_PRELOAD
extern "C" void* mmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    using namespace zen5_turbo;

    init_functions();

    // Check if this is a file-backed mmap that could benefit from huge pages
    if (fd >= 0 && should_use_hugepages(fd, length)) {
        // Get file size to verify we're mapping the whole file
        struct stat st;
        if (fstat(fd, &st) != 0) {
            DEBUG_PRINT("WARNING: Failed to stat fd %d: %s", fd, strerror(errno));
            return real_mmap(addr, length, prot, flags, fd, offset);
        }

        // Only intercept if mapping the whole file from offset 0 (typical for model loading)
        if (offset == 0 && length == (size_t)st.st_size) {
            DEBUG_PRINT("Intercepting mmap for %.2f GB file (using huge pages)",
                    length / (1024.0 * 1024.0 * 1024.0));

            // Allocate anonymous huge pages memory
            void* huge_mem = real_mmap(nullptr, length,
                                       PROT_READ | PROT_WRITE,
                                       MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB,
                                       -1, 0);

            if (huge_mem == MAP_FAILED) {
                // Try without MAP_HUGETLB as fallback
                DEBUG_PRINT("MAP_HUGETLB failed, trying regular anonymous mmap");
                huge_mem = real_mmap(nullptr, length,
                                    PROT_READ | PROT_WRITE,
                                    MAP_PRIVATE | MAP_ANONYMOUS,
                                    -1, 0);

                if (huge_mem == MAP_FAILED) {
                    fprintf(stderr, "[%s] ERROR: Anonymous mmap failed: %s\n",
                            ZEN5_OPTIMIZER_NAME, strerror(errno));
                    return MAP_FAILED;
                }
            } else {
                DEBUG_PRINT("Allocated %.2f GB with MAP_HUGETLB",
                        length / (1024.0 * 1024.0 * 1024.0));
            }

            // Read the file contents into huge pages memory
            DEBUG_PRINT("Loading file contents into huge pages memory...");

            size_t total_read = 0;
            const size_t chunk_size = 256 * 1024 * 1024; // 256MB chunks

            while (total_read < length) {
                size_t to_read = (length - total_read < chunk_size) ? (length - total_read) : chunk_size;
                ssize_t bytes_read = pread(fd, (char*)huge_mem + total_read, to_read, offset + total_read);

                if (bytes_read < 0) {
                    fprintf(stderr, "[%s] ERROR: Failed to read file: %s\n",
                            ZEN5_OPTIMIZER_NAME, strerror(errno));
                    real_munmap(huge_mem, length);
                    return MAP_FAILED;
                }

                if (bytes_read == 0) {
                    fprintf(stderr, "[%s] ERROR: Unexpected EOF at offset %zu\n",
                            ZEN5_OPTIMIZER_NAME, total_read);
                    real_munmap(huge_mem, length);
                    return MAP_FAILED;
                }

                total_read += bytes_read;

                // Progress indicator for large files
                if (total_read % (1024 * 1024 * 1024) == 0) {
                    DEBUG_PRINT("Loaded %.1f GB / %.1f GB",
                            total_read / (1024.0 * 1024.0 * 1024.0),
                            length / (1024.0 * 1024.0 * 1024.0));
                }
            }

            DEBUG_PRINT("Successfully loaded %.2f GB file into huge pages memory",
                    length / (1024.0 * 1024.0 * 1024.0));

            // Set memory protection to match requested (usually PROT_READ for model files)
            // Note: mprotect on huge pages often fails with EINVAL, but this is non-fatal
            if (!(prot & PROT_WRITE)) {
                if (mprotect(huge_mem, length, prot) != 0) {
                    // Silently ignore - this is expected with huge pages
                }
            }

            // Track this allocation so we can handle munmap properly
            track_allocation(huge_mem, length);

            return huge_mem;
        }
    }

    // Not a candidate for huge pages, use regular mmap
    return real_mmap(addr, length, prot, flags, fd, offset);
}

// Our intercepted munmap function
extern "C" int munmap(void* addr, size_t length) {
    using namespace zen5_turbo;

    init_functions();

    // Check if this is one of our tracked allocations
    size_t tracked_size = untrack_allocation(addr);
    if (tracked_size > 0) {
        DEBUG_PRINT("Unmapping %.2f GB huge pages allocation",
                tracked_size / (1024.0 * 1024.0 * 1024.0));
        // Use the tracked size, not the provided length (which might be wrong)
        return real_munmap(addr, tracked_size);
    }

    // Regular munmap
    return real_munmap(addr, length);
}