// Known-input -> known-output checks for the loaders whose upstream tests go through the
// emulator's VFS layer (rsc, spi, mif); same assets and expected values, plain file reads.
#include <catch2/catch.hpp>

#include <common/buffer.h>
#include <common/chunkyseri.h>
#include <loader/mif.h>
#include <loader/rsc.h>
#include <loader/spi.h>

#include <cstdint>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

using namespace eka2l1;

namespace {
    std::vector<std::uint8_t> slurp(const std::string &path) {
        std::ifstream fi(path, std::ios::binary);
        return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(fi), std::istreambuf_iterator<char>());
    }

    void check_rsc(const char *rsc, const std::uint16_t total, const std::string &expected_prefix) {
        std::vector<std::uint8_t> buf = slurp(std::string("loaderassets/") + rsc);
        REQUIRE(!buf.empty());

        common::ro_buf_stream stream(buf.data(), buf.size());
        loader::rsc_file res(reinterpret_cast<common::ro_stream *>(&stream));

        REQUIRE(res.get_total_resources() == total);

        for (std::uint16_t i = 1; i <= total; i++) {
            const std::vector<std::uint8_t> expected = slurp("loaderassets/" + expected_prefix + std::to_string(i) + ".bin");
            REQUIRE(res.read(i) == expected);
        }
    }
}

TEST_CASE("rsc_sample_resources_match_symbian_output", "rsc_file") {
    check_rsc("sample_0xed3e09d5.rsc", 11, "SAMPLE_RESOURCE_DATA_IDX_");
}

TEST_CASE("rsc_rom_sample_resources_match_symbian_output", "rsc_file") {
    check_rsc("javadrmmanager.rsc", 3, "SAMPLE_ROM_RESOURCE_DATA_IDX_");
}

TEST_CASE("rsc_obscure_resource_matches_symbian_output", "rsc_file") {
    std::vector<std::uint8_t> buf = slurp("loaderassets/obscurersc.rsc");
    REQUIRE(!buf.empty());

    common::ro_buf_stream stream(buf.data(), buf.size());
    loader::rsc_file res(reinterpret_cast<common::ro_stream *>(&stream));

    const std::vector<std::uint8_t> expected = slurp("loaderassets/obscurersc.seg1");
    REQUIRE(expected.size() == 181);
    REQUIRE(res.read(1) == expected);
}

TEST_CASE("spi_ecom_registry_entry_is_named", "spi_file") {
    std::vector<std::uint8_t> buf = slurp("loaderassets/ecom-1-0.spi");
    REQUIRE(buf.size() == 108);

    common::chunkyseri seri(buf.data(), buf.size(), common::SERI_MODE_READ);
    loader::spi_file spi(0);

    REQUIRE(spi.do_state(seri));
    REQUIRE(spi.entries.size() == 1);
    REQUIRE(spi.entries[0].name == "emailobservermtmplugin");
}

TEST_CASE("mif_first_entry_is_an_svg_icon_with_header", "mif_file") {
    std::vector<std::uint8_t> data = slurp("loaderassets/itried.mif");
    REQUIRE(!data.empty());

    common::ro_buf_stream stream(data.data(), data.size());
    loader::mif_file miff(reinterpret_cast<common::ro_stream *>(&stream));
    miff.do_parse();

    int dest_size = 0;
    miff.read_mif_entry(0, nullptr, dest_size);
    REQUIRE(dest_size > static_cast<int>(sizeof(loader::mif_icon_header)));

    std::vector<std::uint8_t> buf(dest_size);
    miff.read_mif_entry(0, buf.data(), dest_size);

    const loader::mif_icon_header *header = reinterpret_cast<const loader::mif_icon_header *>(buf.data());
    REQUIRE(header->type == 1);
    REQUIRE(header->data_offset == sizeof(loader::mif_icon_header));
}
