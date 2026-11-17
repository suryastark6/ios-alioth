#!/usr/bin/env python3
"""Extract the DTB (and vendor ramdisk) from an Android vendor_boot image (v3/v4).

    python3 tools/unpack_vendor_boot.py backup/vendor_boot_a.img dtb/boot_unpacked

Writes OUT/dtb (all DTBs as ABL stores them, concatenated; ABL picks the one
that matches the board) and OUT/vendor_ramdisk, and prints the header. The DTB
is what shim/build.sh needs for a header v2 image (DTB=OUT/dtb).
No dependencies.
"""
import os
import struct
import sys

HDR_V3 = struct.Struct('<8sIIIII2048sI16sIIQ')   # through dtb_addr: 2112 bytes
HDR_V4_EXTRA = struct.Struct('<IIII')            # ramdisk table size/num/entry, bootconfig


def pages(n, page):
    return (n + page - 1) // page


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    b = open(src, 'rb').read()
    if b[:8] != b'VNDRBOOT':
        raise SystemExit(f'{src}: not a vendor_boot image (magic {b[:8]!r})')
    (magic, ver, page, kaddr, raddr, rd_size, cmdline, tags, name,
     hdr_size, dtb_size, dtb_addr) = HDR_V3.unpack_from(b, 0)
    if ver not in (3, 4):
        raise SystemExit(f'{src}: vendor_boot header v{ver} not supported (v3/v4)')
    if page not in (2048, 4096, 16384) or hdr_size < HDR_V3.size:
        raise SystemExit(f'{src}: implausible header (page {page}, header_size {hdr_size})')
    extra = HDR_V4_EXTRA.unpack_from(b, HDR_V3.size) if ver == 4 else (0, 0, 0, 0)

    off_rd = pages(hdr_size, page) * page
    off_dtb = off_rd + pages(rd_size, page) * page
    if off_dtb + dtb_size > len(b):
        raise SystemExit(f'{src}: truncated (needs {off_dtb + dtb_size} bytes, has {len(b)})')
    dtb = b[off_dtb:off_dtb + dtb_size]
    if dtb_size and dtb[:4] != b'\xd0\x0d\xfe\xed':
        raise SystemExit(f'{src}: DTB section does not start with FDT magic')

    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'dtb'), 'wb').write(dtb)
    open(os.path.join(out, 'vendor_ramdisk'), 'wb').write(b[off_rd:off_rd + rd_size])

    # Count the concatenated DTBs and read each one's model string cheaply.
    count, pos, models = 0, 0, []
    while pos + 8 <= len(dtb) and dtb[pos:pos + 4] == b'\xd0\x0d\xfe\xed':
        total = struct.unpack_from('>I', dtb, pos + 4)[0]
        blob = dtb[pos:pos + total]
        i = blob.find(b'model\0')
        count += 1
        pos += total
    print(f'header_version  {ver}')
    print(f'page_size       {page}')
    print(f'name            {name.rstrip(bytes(1)).decode(errors="replace")}')
    print(f'cmdline         {cmdline.rstrip(bytes(1)).decode(errors="replace")}')
    print(f'kernel_addr     {kaddr:#x}  ramdisk_addr {raddr:#x}  tags_addr {tags:#x}  dtb_addr {dtb_addr:#x}')
    print(f'vendor_ramdisk  {rd_size} bytes')
    print(f'dtb             {dtb_size} bytes, {count} DTB(s)')
    if ver == 4:
        print(f'v4 ramdisk table {extra[0]} bytes / {extra[1]} entries, bootconfig {extra[3]} bytes')
    print(f'-> {out}/dtb, {out}/vendor_ramdisk')


if __name__ == '__main__':
    main()
