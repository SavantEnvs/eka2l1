#include "log_off.h"
#include <common/buffer.h>
#include <loader/sis_fields.h>

#include <cstdint>
#include <memory>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 16) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    auto stream = std::make_shared<common::ro_buf_stream>(copy.data(), copy.size());
    loader::sis_parser parser(stream);

    parser.parse_header();
    parser.parse_contents();
    return 0;
}
