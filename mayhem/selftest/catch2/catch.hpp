// Minimal stand-in for the Catch2 v2 subset the upstream loader tests use
// (TEST_CASE, SECTION, REQUIRE, REQUIRE_FALSE), so they build without the
// vendored Catch2 submodule. Each failed REQUIRE aborts its test case.
#pragma once

#include <cstdio>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace selftest {
    struct failure : std::runtime_error {
        using std::runtime_error::runtime_error;
    };

    struct test_case {
        std::string name;
        void (*fn)();
    };

    inline std::vector<test_case> &registry() {
        static std::vector<test_case> r;
        return r;
    }

    struct registrar {
        registrar(const char *name, void (*fn)()) { registry().push_back({ name, fn }); }
    };

    // Sections run Catch-style: the test body is re-entered once per section, and
    // only the section whose ordinal matches the current pass executes.
    inline int &section_target() { static int v = 0; return v; }
    inline int &section_seen() { static int v = 0; return v; }

    inline bool enter_section() { return section_seen()++ == section_target(); }

    inline void check(bool ok, const char *expr, const char *file, int line) {
        if (!ok) {
            throw failure(std::string(file) + ":" + std::to_string(line) + ": REQUIRE(" + expr + ") failed");
        }
    }

    inline int run_all() {
        int passed = 0, failed = 0;

        for (const auto &tc : registry()) {
            bool ok = true;
            std::string why;

            for (section_target() = 0;; section_target()++) {
                section_seen() = 0;

                try {
                    tc.fn();
                } catch (const std::exception &e) {
                    ok = false;
                    why = e.what();
                    break;
                }

                if (section_seen() <= section_target() + 1) {
                    break;
                }
            }

            if (ok) {
                passed++;
                std::printf("SELFTEST PASS %s\n", tc.name.c_str());
            } else {
                failed++;
                std::printf("SELFTEST FAIL %s: %s\n", tc.name.c_str(), why.c_str());
            }
        }

        std::printf("SELFTEST SUMMARY passed=%d failed=%d\n", passed, failed);
        return failed == 0 ? 0 : 1;
    }
}

#define SELFTEST_CAT2(a, b) a##b
#define SELFTEST_CAT(a, b) SELFTEST_CAT2(a, b)

#define TEST_CASE(name, ...)                                                                   \
    static void SELFTEST_CAT(selftest_fn_, __LINE__)();                                        \
    static ::selftest::registrar SELFTEST_CAT(selftest_reg_, __LINE__)(name, SELFTEST_CAT(selftest_fn_, __LINE__)); \
    static void SELFTEST_CAT(selftest_fn_, __LINE__)()

#define SECTION(name) if (::selftest::enter_section())

#define REQUIRE(...) ::selftest::check(static_cast<bool>(__VA_ARGS__), #__VA_ARGS__, __FILE__, __LINE__)
#define REQUIRE_FALSE(...) ::selftest::check(!static_cast<bool>(__VA_ARGS__), "!(" #__VA_ARGS__ ")", __FILE__, __LINE__)
