/*
 * cpu_validator.cpp
 *
 * AMD Zen 5 CPU detection using CPUID instruction.
 */

#include "cpu_validator.h"
#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __x86_64__
#include <cpuid.h>
#endif

namespace zen5_turbo {

// Check if current CPU is AMD Zen 5
bool is_zen5_cpu() {
#ifdef __x86_64__
    unsigned int eax, ebx, ecx, edx;

    // Check vendor ID (function 0)
    if (__get_cpuid(0, &eax, &ebx, &ecx, &edx) == 0) {
        return false;
    }

    // Check if AMD ("AuthenticAMD")
    char vendor[13];
    memcpy(vendor, &ebx, 4);
    memcpy(vendor + 4, &edx, 4);
    memcpy(vendor + 8, &ecx, 4);
    vendor[12] = '\0';

    if (strcmp(vendor, "AuthenticAMD") != 0) {
        return false;
    }

    // Get family, model, stepping (function 1)
    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx) == 0) {
        return false;
    }

    // Extract family info
    unsigned int family = (eax >> 8) & 0xF;
    unsigned int extended_family = (eax >> 20) & 0xFF;
    unsigned int model = (eax >> 4) & 0xF;
    unsigned int extended_model = (eax >> 16) & 0xF;

    // Calculate display family
    unsigned int display_family = family;
    if (family == 0xF) {
        display_family = family + extended_family;
    }

    // Calculate display model
    unsigned int display_model = model;
    if (family == 0xF || family == 0x6) {
        display_model = (extended_model << 4) + model;
    }

    // AMD Zen 5 is Family 26 (0x1A)
    // Models: 0x40-0x4F (Granite Ridge/Ryzen 9000), 0x20-0x2F (Strix Point/Ryzen AI 300)
    if (display_family == 0x1A) {
        // Model 0x44 = Granite Ridge (Ryzen 9000 series)
        // Model 0x24 = Strix Point (Ryzen AI 300 series)
        return true; // Accept all Family 26 models as Zen 5
    }

    return false;
#else
    // Not x86_64 architecture
    return false;
#endif
}

// Validate CPU and exit if not Zen 5
void validate_zen5_or_exit() {
    if (!is_zen5_cpu()) {
        fprintf(stderr, "[%s] ERROR: CPU is not AMD Zen 5\n", ZEN5_OPTIMIZER_NAME);
        fprintf(stderr, "[%s] This optimizer requires AMD Zen 5 (Family 25h)\n", ZEN5_OPTIMIZER_NAME);
        fprintf(stderr, "[%s] Supported CPUs: Ryzen 9000 series, Ryzen AI 300 series\n", ZEN5_OPTIMIZER_NAME);
        exit(1);
    }

    DEBUG_PRINT("CPU validation: OK (AMD Zen 5 detected)");
}

} // namespace zen5_turbo