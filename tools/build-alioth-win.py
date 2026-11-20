#!/usr/bin/env python3
"""Build alioth test images on Windows (no WSL), like tools/build-alioth.sh.

Needs:
  - Arm GNU Toolchain for Windows, aarch64-none-elf (developer.arm.com),
    unzipped; pass its bin folder with --toolchain
  - AOSP mkbootimg.py (system/tools/mkbootimg, with its gki/ folder); pass
    it with --mkbootimg

    python tools/build-alioth-win.py m1 [--disp full|none|kick]
    python tools/build-alioth-win.py m3 KERNEL [--cpus N]
    python tools/build-alioth-win.py m5 KERNEL [--cpus N]   (root on userdata)

Header v3 only (ABL takes the DTB from the phone's vendor_boot). Output:
<repository>/../out/new/alioth-<milestone>-v3[-disp<mode>].img (next to the
images the Linux script built, never over them). The C flags, link and image layout are the ones of
shim/build.sh.
"""
import argparse
import glob
import gzip
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHIM = os.path.join(ROOT, 'shim')
SOURCES = ['start.S', 'shim.c', 'console.c', 'mmu.c', 'fdt.c', 'loader.c', 'ufs.c', 'display.c']
DISP = {'full': '', 'none': '-DDISP_TEST=1', 'kick': '-DDISP_TEST=2'}
ARGS = 'debug=0xc serial=3 cpus={cpus} keepsyms=1 -enable_kprintf_spam -noprogress wdt=-1'
# M5 additions, as tools/build-alioth.sh (see docs/SWEET-README.md)
M5_ARGS = (' rd=ufsroot0 ufsrw=1 rootrw=1 unentitled_ios_sim_launch=1 ignition_level=1'
           ' wdt_test=no_user_checkin launchd_unsecure_cache=1 sweetfb_hz=30')


def run(cmd, **kw):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)
    if r.returncode:
        sys.exit(f'failed: {" ".join(cmd)}\n{r.stdout}')
    return r.stdout


def find_tool(bindir, name):
    for prefix in ('aarch64-none-elf-', 'aarch64-linux-gnu-'):
        for ext in ('.exe', ''):
            p = os.path.join(bindir, prefix + name + ext)
            if os.path.isfile(p):
                return p
    sys.exit(f'{name} not found in {bindir}')


def empty_cpio_gz():
    # newc archive holding only '.' and the trailer, as `find . | cpio -o -H newc`
    def entry(name, mode, nlink):
        name = name.encode() + b'\0'
        hdr = b'070701' + b''.join(b'%08X' % v for v in (
            0, mode, 0, 0, nlink, 0, 0, 0, 0, 0, 0, len(name), 0))
        data = hdr + name
        return data + b'\0' * (-len(data) % 4)
    raw = entry('.', 0o40755, 2) + entry('TRAILER!!!', 0, 1)
    raw += b'\0' * (-len(raw) % 512)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=9, mtime=0) as g:
        g.write(raw)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('milestone', choices=['m1', 'm3', 'm5'])
    ap.add_argument('kernel', nargs='?')
    ap.add_argument('--disp', choices=list(DISP), default='full')
    ap.add_argument('--cpus', type=int, default=1, choices=range(1, 9))
    ap.add_argument('--extra', default='', help='more boot-args, e.g. "sweetsample=lsd,SpringBoard"')
    ap.add_argument('--tag', default='', help='suffix for the image name')
    ap.add_argument('--gpu-fw', default='', help='folder with the phone's a650_* GPU firmware, put into the ADT')
    ap.add_argument('--noconsole', action='store_true',
                    help='sweetfb_noconsole=1: no kernel text over the iOS GUI (panics are still drawn)')
    ap.add_argument('--toolchain', default=os.path.join(ROOT, '..', 'toolchain', 'bin'),
                    help='folder with aarch64-none-elf-gcc.exe')
    ap.add_argument('--mkbootimg', default=os.path.join(ROOT, '..', 'toolchain', 'mkbootimg', 'mkbootimg.py'))
    a = ap.parse_args()
    kernel_ms = a.milestone in ('m3', 'm5')
    args = ARGS.format(cpus=a.cpus) + (M5_ARGS if a.milestone == 'm5' else '') +         (' sweetfb_noconsole=1' if a.noconsole else '') + (' ' + a.extra if a.extra else '')
    if kernel_ms and not (a.kernel and os.path.isfile(a.kernel)):
        sys.exit(f'{a.milestone} needs the kernel file (kernel.development.sweet from the kernel branch)')
    tc = os.path.abspath(a.toolchain)
    if not os.path.isdir(tc):
        cand = glob.glob(os.path.join(ROOT, '..', 'toolchain', '*', 'bin'))
        if not cand:
            sys.exit(f'toolchain bin folder not found: {tc}')
        tc = os.path.abspath(cand[0])
    cc, objcopy, readelf, nm = (find_tool(tc, t) for t in ('gcc', 'objcopy', 'readelf', 'nm'))

    out = os.path.join(SHIM, 'out')
    os.makedirs(out, exist_ok=True)
    cflags = ['-DBOARD_ALIOTH'] + ([DISP[a.disp]] if DISP[a.disp] else []) + \
        '-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra'.split()
    objs = []
    for f in SOURCES:
        o = os.path.join(out, os.path.splitext(f)[0] + '.o')
        warn = run([cc, *cflags, '-c', os.path.join(SHIM, f), '-o', o])
        if warn.strip():
            print(warn.strip())
        objs.append(o)
    # Position independent: only start.o (the header's image_size) may hold
    # an absolute address.
    rel = run([readelf, '-r', *objs[1:]])
    if 'ABS64' in rel:
        sys.exit('absolute relocations in C objects:\n' + rel)
    elf = os.path.join(out, 'shim.elf')
    run([cc, *cflags, '-static', '-T', os.path.join(SHIM, 'shim.ld'), '-Wl,--build-id=none',
         '-Wl,--no-warn-rwx-segments', '-Wl,-N', *objs, '-o', elf])
    image = os.path.join(out, 'Image')
    run([objcopy, '-O', 'binary', elf, image])
    end = next(int(l.split()[0], 16) for l in run([nm, elf]).splitlines() if l.split()[-1] == '_end')
    with open(image, 'r+b') as f:
        f.truncate(end)

    ramdisk = os.path.join(out, 'ramdisk.bin')
    if kernel_ms:
        adt = os.path.join(out, 'alioth.adt')
        run([sys.executable, os.path.join(HERE, 'mkadt.py'), adt, '--board', 'alioth', '--highmem'] +
            (['--gpu-fw', a.gpu_fw] if a.gpu_fw else []))
        run([sys.executable, os.path.join(HERE, 'mkpayload.py'), a.kernel, adt, ramdisk,
             '--cmdline', args])
    else:
        open(ramdisk, 'wb').write(empty_cpio_gz())

    dest = os.path.join(ROOT, '..', 'out', 'new')
    os.makedirs(dest, exist_ok=True)
    img = os.path.join(dest, f'alioth-{a.milestone}-v3' + (f'-disp{a.disp}' if DISP[a.disp] else '') +
                       (f'-cpus{a.cpus}' if kernel_ms and a.cpus > 1 else '') +
                       ('-noconsole' if a.noconsole else '') + (f'-{a.tag}' if a.tag else '') + '.img')
    run([sys.executable, a.mkbootimg, '--header_version', '3', '--kernel', image, '--ramdisk', ramdisk,
         '--os_version', '17.0.0', '--os_patch_level', '2035-06', '--cmdline', 'console=null',
         '--output', img])
    print(f'{os.path.abspath(img)}  ({os.path.getsize(img)} bytes, Image {end} bytes)')
    if kernel_ms:
        print('boot-args: ' + args)


if __name__ == '__main__':
    main()
