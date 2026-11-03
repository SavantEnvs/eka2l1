# sis: `uncompressed_size` of a compressed field is used as an allocation size

`sis_parser::parse_compressed` (`src/emu/loader/src/sis_fields.cpp:268`) reads a 64-bit `uncompressed_size` from
the file and calls `compressed.uncompressed_data.resize(compressed.uncompressed_size)` for non-deflated
data, with no bound. Depending on the value: 3522711 hits ASan `allocation-size-too-big`, 3522712 is
libFuzzer `out-of-memory (malloc(8589934627))`, and 3521237 is an uncaught `std::length_error` from
`vector::resize` (Mayhem CWE-248; under libFuzzer it surfaces as `deadly signal` because `terminate()` aborts).
Same unchecked size in all three.

Impact: a crafted `.sis`/`.sisx` makes the parser allocate gigabytes or throw out of the loader (denial of service).

Upstream fix: compare `uncompressed_size` with the bytes left in the stream (and a sane maximum) before the `resize`.

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522711.sis`
- `defect-3522712.sis`
- `defect-3521237.sis`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_sis /c/defect-<id>.sis
```
Use the libFuzzer binary: its default 2 GiB malloc/RSS limit is what Mayhem reports as
`out-of-memory`. `/mayhem/fuzz_sis-standalone` has no limit, so on a host with enough memory the
allocation can succeed (or the process is OOM-killed, exit 137); to see the allocating frame there, run it
with `ASAN_OPTIONS=max_allocation_size_mb=1024` (a local diagnostic, not part of the build).
