#include "log_off.h"
#include <common/buffer.h>
#include <loader/nvg.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 4) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    common::ro_buf_stream in(copy.data(), copy.size());
    common::wo_growable_buf_stream out;
    std::vector<loader::nvg_convert_error_description> errors;
    loader::convert_nvg_to_svg(in, out, errors);
    return 0;
}
