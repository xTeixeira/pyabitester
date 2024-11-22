import pyabigail

environment = pyabigail.Environment()
print(f"Environment: {environment}")

origin = pyabigail.Origin.ELF
print(f"Origin: {origin}")

status = pyabigail.Status.OK
print(f"Status: {status}")

reader = pyabigail.create_best_elf_based_reader("./pyabigail.so", [], environment, origin, False, False)
print(f"Reader: {reader}")

# breakpoint()
