#include "log_off.h"
#include <common/buffer.h>
#include <loader/gdr.h>

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
    loader::gdr::file_store store;
    loader::gdr::parse_store(&stream, store);
    return 0;
}
