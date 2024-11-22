clean:
	rm -rf *.so
build: clean
	g++ --std=c++17 --shared -fPIC        \
	`python3 -m pybind11 --includes`      \
	-I/usr/include/libabigail/libabigail  \
	-labigail                             \
	module.cpp                            \
	-o pyabigail.so
