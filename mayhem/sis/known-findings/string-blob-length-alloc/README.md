# sis: string and blob field lengths are used as allocation sizes

`sis_parser::parse_string` (`src/emu/loader/src/sis_fields.cpp:418`) does
`unicode_string.resize(len / 2)` and `sis_parser::parse_blob` (`sis_fields.cpp:526`) does
`raw_data.resize(len)`, where `len` is the 64-bit `len_low | len_high << 32` field read from the file.
Neither compares it with the remaining input. Both requests are far above ASan's maximum
(`allocation-size-too-big`: 3522719 asks for 0x646d9ce5000002 bytes, 3522714 for 0x6d7f6564e5349bc8 bytes).

Defects 3522719 (`parse_string`) and 3522714 (`parse_blob`).

Impact: a crafted `.sis`/`.sisx` makes the parser allocate gigabytes or abort (denial of service).

Upstream fix: reject a field whose length exceeds the bytes left in the stream before resizing.

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522719.sis`
- `defect-3522714.sis`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_sis /c/defect-<id>.sis
```
Use the libFuzzer binary: its default 2 GiB malloc/RSS limit is what Mayhem reports as
`out-of-memory`. `/mayhem/fuzz_sis-standalone` has no limit, so on a host with enough memory the
allocation can succeed (or the process is OOM-killed, exit 137); to see the allocating frame there, run it
with `ASAN_OPTIONS=max_allocation_size_mb=1024` (a local diagnostic, not part of the build).
