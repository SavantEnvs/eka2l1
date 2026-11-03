# gdr: typeface and bitmap-header counts are used as allocation sizes

`parse_typeface_list_headers` (`src/emu/loader/src/gdr.cpp:327`) reads a 32-bit `header_count` and calls
`headers.resize(header_count)`; `parse_typeface_list_header` (`gdr.cpp:309`) does the same with
`num_typeface_font_bitmap_header` for `bitmap_headers_`. `typeface_header` is 64 bytes and `typeface_font_bitmap_header` 12, so counts near 2^32 and 2^31 ask for hundreds of GiB and about 24 GiB: libFuzzer reports `out-of-memory (malloc(274877897216))` for
3522553 (`gdr.cpp:327`) and `malloc(25769803752)` for 3522554 (`gdr.cpp:309`).

Impact: a crafted GDR (Symbian font store) makes the parser allocate until it is killed (denial of service).

Upstream fix: reject a count that exceeds the bytes remaining in the stream divided by the minimum element size, before the `resize`.

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522553.gdr`
- `defect-3522554.gdr`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_gdr /c/defect-<id>.gdr
```
Use the libFuzzer binary: its default 2 GiB malloc/RSS limit is what Mayhem reports as
`out-of-memory`. `/mayhem/fuzz_gdr-standalone` has no limit, so on a host with enough memory the
allocation can succeed (or the process is OOM-killed, exit 137); to see the allocating frame there, run it
with `ASAN_OPTIONS=max_allocation_size_mb=1024` (a local diagnostic, not part of the build).
