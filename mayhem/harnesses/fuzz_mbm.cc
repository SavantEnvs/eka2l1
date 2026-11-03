#include "log_off.h"
#include <common/buffer.h>
#include <loader/mbm.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 12) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    common::ro_buf_stream stream(copy.data(), copy.size());
    loader::mbm_file mbm(&stream);

    if (!mbm.do_read_headers() || !mbm.valid()) {
        return 0;
    }

    const std::size_t count = mbm.trailer.sbm_offsets.size() < 8 ? mbm.trailer.sbm_offsets.size() : 8;
    for (std::size_t i = 0; i < count; i++) {
        // Like the FBS server: size the destination from the header geometry, rounded up to 4 bytes. The
        // null-destination probe is skipped: the RLE fast route computes dest + size on a null pointer.
        const auto &hdr = mbm.sbm_headers[i];
        if (hdr.size_pixels.x <= 0 || hdr.size_pixels.y <= 0 || hdr.bit_per_pixels == 0 || hdr.bit_per_pixels > 32) {
            continue;
        }

        const std::uint64_t byte_width = ((static_cast<std::uint64_t>(hdr.size_pixels.x) * hdr.bit_per_pixels + 31) / 32) * 4;
        const std::uint64_t full_size = byte_width * static_cast<std::uint64_t>(hdr.size_pixels.y);
        if (full_size > (16u << 20)) {
            continue;
        }

        std::size_t avail = (static_cast<std::size_t>(full_size) + 3) & ~static_cast<std::size_t>(3);
        std::vector<std::uint8_t> dest(avail);
        mbm.read_single_bitmap(i, dest.data(), avail);
    }

    return 0;
}
