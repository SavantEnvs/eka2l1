#include "log_off.h"
#include <common/buffer.h>
#include <loader/mif.h>

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
    loader::mif_file mif(&stream);

    if (!mif.do_parse()) {
        return 0;
    }

    const std::size_t count = mif.idxs_.size() < 8 ? mif.idxs_.size() : 8;
    for (std::size_t i = 0; i < count; i++) {
        int entry_size = 0;
        if (!mif.read_mif_entry(i, nullptr, entry_size) || entry_size <= 0 || entry_size > (16 << 20)) {
            continue;
        }

        std::vector<std::uint8_t> entry(entry_size);
        if (!mif.read_mif_entry(i, entry.data(), entry_size)) {
            continue;
        }

        common::wo_growable_buf_stream out;
        loader::convert_mif_icon_to_svg(entry.data(), static_cast<std::size_t>(entry_size), out);
    }

    return 0;
}
