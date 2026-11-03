#include "log_off.h"
#include <common/buffer.h>
#include <common/bytepair.h>
#include <common/dictcomp.h>
#include <common/runlen.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 3) {
        return -1;
    }

    const std::uint8_t selector = data[0] % 3;
    std::vector<std::uint8_t> copy(data + 1, data + size);
    const std::size_t len = copy.size();

    if (selector == 0) {
        std::vector<std::uint8_t> dest(4096);
        common::bytepair_decompress(dest.data(), static_cast<unsigned int>(dest.size()), copy.data(), static_cast<unsigned int>(len));
    } else if (selector == 1) {
        common::ro_buf_stream in(copy.data(), len);
        common::wo_growable_buf_stream out;
        switch (copy[0] % 4) {
        case 0: decompress_rle<8>(&in, &out); break;
        case 1: decompress_rle<16>(&in, &out); break;
        case 2: decompress_rle<24>(&in, &out); break;
        default: decompress_rle<32>(&in, &out); break;
        }
    } else {
        common::dictcomp dict(copy.data(), 0, static_cast<int>(len), 1 + (copy[0] % 8));
        int out_size = dict.calculate_decompress_size(false);
        if (out_size > 0 && out_size <= (1 << 20)) {
            std::vector<std::uint8_t> dest(out_size);
            dict.read(dest.data(), out_size, false);
        }
    }

    return 0;
}
