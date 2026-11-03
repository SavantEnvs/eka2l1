#include "log_off.h"
#include <common/buffer.h>
#include <loader/rsc.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 8) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    common::ro_buf_stream stream(copy.data(), copy.size());
    loader::rsc_file rsc(&stream);

    const int total = rsc.get_total_resources();
    const int limit = total < 64 ? total : 64;
    for (int u = 1; u <= 3; u++) {
        rsc.get_uid(u);
    }
    rsc.confirm_signature();

    for (int i = 1; i <= limit; i++) {
        rsc.read(i);
    }

    return 0;
}
