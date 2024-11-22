// pybind: main header
#include <pybind11/pybind11.h>

// pybind: auto type conversions
#include <pybind11/chrono.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include <pybind11/stl/filesystem.h>
#include <pybind11/stl_bind.h>
// #include <pybind11/eigen.h>

// libabigail headers
#include <libabigail/libabigail/abg-corpus.h>
#include <libabigail/libabigail/abg-elf-reader.h>
#include <libabigail/libabigail/abg-fe-iface.h>
#include <libabigail/libabigail/abg-ir.h>
#include <libabigail/libabigail/abg-tools-utils.h>

namespace py = pybind11;

std::vector<char **> convert_to_char_ptr_vector(const std::vector<std::string> &strings)
{
    std::vector<char **> result;
    for (const auto &s : strings)
    {
        char *c_str = new char[s.size() + 1];
        std::strcpy(c_str, s.c_str());
        result.push_back(new char *(c_str));
    }
    return result;
}

void cleanup_char_ptr_vector(std::vector<char **> &vec)
{
    for (auto char_ptr : vec)
    {
        delete[] *char_ptr;
        delete char_ptr;
    }
}

std::shared_ptr<abigail::elf::reader> wrapped_create_best_elf_based_reader(
    const std::string &elf_file_path, const std::vector<std::string> &debug_info_root_paths,
    abigail::ir::environment &env, abigail::corpus::origin requested_debug_info_kind, bool show_all_types,
    bool linux_kernel_mode = false)
{

    auto converted_paths = convert_to_char_ptr_vector(debug_info_root_paths);

    auto result = abigail::tools_utils::create_best_elf_based_reader(
        elf_file_path, converted_paths, env, requested_debug_info_kind, show_all_types, linux_kernel_mode);

    cleanup_char_ptr_vector(converted_paths);

    return result;
}

PYBIND11_MODULE(pyabigail, m)
{
    py::class_<abigail::ir::environment>(m, "Environment").def(py::init<>());

    py::class_<abigail::elf::reader>(m, "Reader").def("read_corpus", &abigail::elf::reader::read_corpus);

    py::enum_<abigail::fe_iface::status>(m, "Status")
        .value("ALT_DEBUG_INFO_NOT_FOUND", abigail::fe_iface::STATUS_ALT_DEBUG_INFO_NOT_FOUND)
        .value("DEBUG_INFO_NOT_FOUND", abigail::fe_iface::STATUS_DEBUG_INFO_NOT_FOUND)
        .value("NO_SYMBOLS_FOUND", abigail::fe_iface::STATUS_NO_SYMBOLS_FOUND)
        .value("OK", abigail::fe_iface::STATUS_OK)
        .value("UNKNOWN", abigail::fe_iface::STATUS_UNKNOWN);

    py::enum_<abigail::corpus::origin>(m, "Origin")
        .value("ARTIFICIAL", abigail::corpus::origin::ARTIFICIAL_ORIGIN)
        .value("BTF", abigail::corpus::origin::BTF_ORIGIN)
        .value("CTF", abigail::corpus::origin::CTF_ORIGIN)
        .value("DWARF", abigail::corpus::origin::DWARF_ORIGIN)
        .value("ELF", abigail::corpus::origin::ELF_ORIGIN)
        .value("LINUX_KERNEL_BINARY", abigail::corpus::origin::LINUX_KERNEL_BINARY_ORIGIN)
        .value("NATIVE_XML", abigail::corpus::origin::NATIVE_XML_ORIGIN);

    m.def("create_best_elf_based_reader", &wrapped_create_best_elf_based_reader, py::arg("elf_file_path"),
          py::arg("debug_info_root_paths"), py::arg("env"), py::arg("requested_debug_info_kind"),
          py::arg("show_all_types"), py::arg("linux_kernel_mode") = false,
          R"pbdoc(
          Create the best ELF-based reader for a given ELF file path and environment.

          Parameters:
              elf_file_path (str): Path to the ELF file.
              debug_info_root_paths (list[str]): List of debug info root paths.
              env (Environment): ABI environment.
              requested_debug_info_kind (Origin): Requested debug info kind.
              show_all_types (bool): Flag to show all types.
              linux_kernel_mode (bool): Optional flag for Linux kernel mode.
          Returns:
              ELF-based reader instance.
          )pbdoc");
};
