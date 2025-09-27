# Makefile for zen5_optimizer
#
# Simple Unix-style build system for AMD Zen 5 optimizer library.

# Compiler settings (matching ai-experiments)
CXX = g++-14
CXXFLAGS = -std=c++17 -march=znver5 -mtune=znver5 -O3 -fPIC -Wall -Wextra \
          -ffast-math -fno-finite-math-only
LDFLAGS = -shared -ldl -lpthread

# Directories
SRC_DIR = src
BUILD_DIR = build
TEST_DIR = tests
PREFIX = /usr/local

# Target library
LIB_NAME = libzen5_optimizer.so
LIB_PATH = $(BUILD_DIR)/$(LIB_NAME)

# Source files
SOURCES = $(SRC_DIR)/zen5_optimizer.cpp \
          $(SRC_DIR)/memory/hugepage_wrapper.cpp \
          $(SRC_DIR)/cpu_validator.cpp

OBJECTS = $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(SOURCES))

# Test programs
TEST_SOURCES = $(TEST_DIR)/test_load.cpp \
               $(TEST_DIR)/test_cpu.cpp \
               $(TEST_DIR)/test_hugepage.cpp

TEST_PROGRAMS = $(patsubst $(TEST_DIR)/%.cpp,$(BUILD_DIR)/%,$(TEST_SOURCES))

# Default target
all: $(LIB_PATH)

# Build library
$(LIB_PATH): $(OBJECTS)
	@echo "[BUILD] Linking $@"
	@$(CXX) $(LDFLAGS) -o $@ $^
	@echo "[OK] Library built: $@"

# Compile source files
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(dir $@)
	@echo "[BUILD] Compiling $<"
	@$(CXX) $(CXXFLAGS) -c -o $@ $<

# Build test programs
$(BUILD_DIR)/test_%: $(TEST_DIR)/test_%.cpp
	@mkdir -p $(BUILD_DIR)
	@echo "[BUILD] Compiling test: $@"
	@$(CXX) -std=c++17 -o $@ $< -ldl

# Run tests
test: $(LIB_PATH) $(TEST_PROGRAMS)
	@echo "[TEST] Running tests..."
	@for test in $(TEST_PROGRAMS); do \
		echo "[RUN] $$(basename $$test)"; \
		LD_LIBRARY_PATH=$(BUILD_DIR) $$test || exit 1; \
	done
	@echo "[OK] All tests passed"

# Install library
install: $(LIB_PATH)
	@echo "[INSTALL] Installing to $(PREFIX)/lib"
	@install -D -m 755 $(LIB_PATH) $(PREFIX)/lib/$(LIB_NAME)
	@echo "[OK] Installed to $(PREFIX)/lib/$(LIB_NAME)"

# Uninstall library
uninstall:
	@echo "[UNINSTALL] Removing $(PREFIX)/lib/$(LIB_NAME)"
	@rm -f $(PREFIX)/lib/$(LIB_NAME)

# Clean build artifacts
clean:
	@echo "[CLEAN] Removing build artifacts"
	@rm -rf $(BUILD_DIR)
	@echo "[OK] Clean complete"

# Show usage information
help:
	@echo "zen5_optimizer Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all       - Build the library (default)"
	@echo "  test      - Build and run tests"
	@echo "  install   - Install library to $(PREFIX)/lib"
	@echo "  uninstall - Remove installed library"
	@echo "  clean     - Remove build artifacts"
	@echo "  help      - Show this help message"
	@echo ""
	@echo "Variables:"
	@echo "  PREFIX    - Installation prefix (default: /usr/local)"
	@echo "  CXX       - C++ compiler (default: g++)"

.PHONY: all test install uninstall clean help