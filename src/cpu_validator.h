/*
 * cpu_validator.h
 *
 * AMD Zen 5 CPU detection and validation.
 * Ensures the library only runs on the target architecture.
 */

#pragma once

namespace zen5_turbo {

// Check if current CPU is AMD Zen 5 (Family 25h)
bool is_zen5_cpu();

// Validate CPU and exit if not Zen 5
void validate_zen5_or_exit();

} // namespace zen5_turbo