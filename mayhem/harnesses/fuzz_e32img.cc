#include "log_off.h"
#include <common/buffer.h>
#include <loader/e32img.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 16) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    common::ro_buf_stream stream(copy.data(), copy.size());

    if (!loader::is_e32img(&stream)) {
        return 0;
    }

    stream.seek(0, common::beg);
    loader::parse_e32img(&stream, true);
    return 0;
}
