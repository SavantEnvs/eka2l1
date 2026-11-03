# rom: directory with a size larger than its entries grows `entries` without bound

`read_rom_dir` (`src/emu/loader/src/rom.cpp:220`) loops `while (tell() - old_off < dir.size)` and
`push_back`s a `rom_entry` per iteration. `dir.size` comes from the file. When the entry read fails (end of
stream, `ro_buf_stream::read` returns 0 and does not advance) `read_rom_entry` returns an empty entry without advancing the stream, so the loop condition never
changes and `dir.entries` grows until the allocation fails: libFuzzer reports `out-of-memory
(malloc(2415919104))`; with `ASAN_OPTIONS=max_allocation_size_mb=1024` on the standalone binary the allocating frame is `read_rom_dir` `rom.cpp:220` (a 0x48000000-byte vector growth).

Defect 3522627, "Memory Allocation with Excessive Size Value" (CWE-789).

Impact: a crafted ROM image makes the loader allocate until the process is killed (denial of service).

Upstream fix: `break` out of the `read_rom_dir` loop when `read_rom_entry` fails to read the entry header (or `stream->tell()` did not advance).

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522627.rom`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_rom /c/defect-<id>.rom
```
Use the libFuzzer binary: its default 2 GiB malloc/RSS limit is what Mayhem reports as
`out-of-memory`. `/mayhem/fuzz_rom-standalone` has no limit, so on a host with enough memory the
allocation can succeed (or the process is OOM-killed, exit 137); to see the allocating frame there, run it
with `ASAN_OPTIONS=max_allocation_size_mb=1024` (a local diagnostic, not part of the build).
