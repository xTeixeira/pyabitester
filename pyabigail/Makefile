clean:
	@rm -rf *.so
	@echo "=== Removed all shared object files (.so) ==="
build: clean
	@echo "=== Building ==="
	@g++ --std=c++17 --shared -fPIC        \
	`python3 -m pybind11 --includes`      \
	-I/usr/include/libabigail/libabigail  \
	-labigail                             \
	module.cpp                            \
	-o pyabigail.so
	@echo "=== Compilation successful ==="
check: clean build
	@echo "=== Running check.py ==="
	@python3 check.py
format:
	@clang-format --style=LLVM -i *.cpp
	@echo "=== Formatted code with clang-format ==="
