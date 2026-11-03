#include "log_off.h"
#include <common/buffer.h>
#include <loader/rom.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

namespace {
    // The defragmenter writes the rebuilt image to a file in real use; a counting sink keeps the harness
    // from holding up to 4 GiB in memory while still running every write path.
    class counting_sink : public common::wo_stream {
        std::uint64_t written_ = 0;

    public:
        std::uint64_t write(const void *, const std::uint64_t size) override {
            written_ += size;
            return size;
        }

        void seek(const std::int64_t, common::seek_where) override {}
        bool valid() override { return true; }
        std::uint64_t left() override { return 0; }
        std::uint64_t tell() override { return written_; }
        std::uint64_t size() override { return written_; }
    };
}

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 256) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);

    common::ro_buf_stream stream(copy.data(), copy.size());
    loader::load_rom(&stream);

    common::ro_buf_stream defrag_in(copy.data(), copy.size());
    counting_sink sink;
    loader::defrag_rom(&defrag_in, &sink);
    return 0;
}
