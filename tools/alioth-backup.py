#!/usr/bin/env python3
"""Back up alioth and collect its hardware description (Windows, macOS, Linux).

Run with the phone in OrangeFox or TWRP (booted with `fastboot boot`, nothing
flashed) and USB connected:

    python tools/alioth-backup.py [--adb PATH] [--out backup]

Read-only on the phone. It saves:
  backup/        persist, modemst1/2, fsg, fsc (IMEI and calibration: keep
                 these safe, they cannot be downloaded anywhere), boot,
                 dtbo, vbmeta, vendor_boot of the active slot
  dtb/alioth-live.dtb     the device tree ABL booted with (/sys/firmware/fdt)
  dtb/alioth-info.txt     slot, RAM, firmware, partition table, cmdline
  dtb/alioth-scan.txt     tools/fdt-scan.py output
  dtb/boot_unpacked/dtb   stock DTB from vendor_boot (for HEADER=2 images)
Each partition is checked against a sha256 computed on the phone.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARTS = ['persist', 'modemst1', 'modemst2', 'fsg', 'fsc', 'boot', 'dtbo', 'vbmeta', 'vendor_boot']
BYNAME = '/dev/block/bootdevice/by-name'


def find_adb(given):
    if given:
        return given
    for name in ('adb', 'adb.exe'):
        p = shutil.which(name)
        if p:
            return p
    for d in (os.path.join(ROOT, 'platform-tools'), os.path.join(ROOT, '..', 'platform-tools'),
              os.path.expanduser('~/platform-tools'), r'C:\platform-tools'):
        for name in ('adb.exe', 'adb'):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    raise SystemExit('adb not found: install Android platform-tools and pass --adb PATH\\adb.exe')


def run(adb, *args, binary=False, check=True):
    r = subprocess.run([adb, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and r.returncode:
        raise SystemExit(f'adb {" ".join(args)} failed: {r.stderr.decode(errors="replace").strip()}')
    return r.stdout if binary else r.stdout.decode(errors='replace').replace('\r', '')


def sh(adb, cmd, check=False):
    return run(adb, 'shell', cmd, check=check).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--adb')
    ap.add_argument('--out', default=os.path.join(ROOT, 'backup'))
    ap.add_argument('--skip-partitions', action='store_true', help='only collect the device tree and info')
    a = ap.parse_args()
    adb = find_adb(a.adb)
    dtbdir = os.path.join(ROOT, 'dtb')
    os.makedirs(dtbdir, exist_ok=True)

    print(f'adb: {adb}')
    run(adb, 'wait-for-device')
    device = sh(adb, 'getprop ro.product.device') or sh(adb, 'getprop ro.build.product')
    print(f'device: {device or "unknown"}')
    if 'alioth' not in (device or ''):
        print('warning: this does not look like alioth (POCO F3 / K40 / Mi 11X); continuing', file=sys.stderr)
    if sh(adb, 'id -u') != '0':
        raise SystemExit('adb is not root: boot OrangeFox/TWRP (fastboot boot recovery.img) and retry')
    slot = sh(adb, 'getprop ro.boot.slot_suffix')
    print(f'active slot: {slot or "none"}')

    # Everything a later step may need, in one text file.
    info = []
    for title, cmd in [
        ('slot', 'getprop ro.boot.slot_suffix'),
        ('hwname / hwc', 'getprop ro.boot.hwname; getprop ro.boot.hwc; getprop ro.boot.hwversion'),
        ('firmware', 'getprop ro.build.version.incremental; getprop ro.build.fingerprint; getprop ro.boot.verifiedbootstate'),
        ('meminfo', 'head -3 /proc/meminfo'),
        ('cmdline', 'cat /proc/cmdline'),
        ('by-name', f'ls -l {BYNAME}/'),
        ('partitions', 'cat /proc/partitions'),
        ('userdata', f'readlink -f {BYNAME}/userdata'),
        ('iomem', 'cat /proc/iomem'),
    ]:
        info.append(f'== {title}\n{sh(adb, cmd)}\n')
    open(os.path.join(dtbdir, 'alioth-info.txt'), 'w', encoding='utf-8').write('\n'.join(info))
    print(f'info -> {os.path.join(dtbdir, "alioth-info.txt")}')

    fdt = run(adb, 'exec-out', 'cat /sys/firmware/fdt', binary=True)
    if fdt[:4] != b'\xd0\x0d\xfe\xed':
        raise SystemExit('could not read /sys/firmware/fdt (no FDT magic)')
    live = os.path.join(dtbdir, 'alioth-live.dtb')
    open(live, 'wb').write(fdt)
    print(f'live device tree -> {live} ({len(fdt)} bytes)')

    if not a.skip_partitions:
        os.makedirs(a.out, exist_ok=True)
        print(f'partitions -> {a.out}')
        for part in PARTS:
            dev = None
            for cand in (part + slot, part, part + '_a'):
                if cand and sh(adb, f'[ -e {BYNAME}/{cand} ] && echo y') == 'y':
                    dev = cand
                    break
            if not dev:
                print(f'  skip {part} (not found)')
                continue
            data = run(adb, 'exec-out', f'dd if={BYNAME}/{dev} bs=1048576 2>/dev/null', binary=True)
            want = sh(adb, f'sha256sum {BYNAME}/{dev}').split()[0] if data else ''
            got = hashlib.sha256(data).hexdigest()
            if not data or got != want:
                raise SystemExit(f'checksum mismatch for {dev} (phone {want}, PC {got}): retry with a different USB port/cable')
            open(os.path.join(a.out, dev + '.img'), 'wb').write(data)
            print(f'  {dev}: {len(data) >> 20} MiB, sha256 ok')

        vb = None
        for cand in ('vendor_boot' + slot, 'vendor_boot', 'vendor_boot_a'):
            p = os.path.join(a.out, cand + '.img')
            if os.path.isfile(p):
                vb = p
                break
        if vb:
            r = subprocess.run([sys.executable, os.path.join(HERE, 'unpack_vendor_boot.py'), vb,
                                os.path.join(dtbdir, 'boot_unpacked')], stdout=subprocess.PIPE, text=True)
            print(r.stdout.strip())

    r = subprocess.run([sys.executable, os.path.join(HERE, 'fdt-scan.py'), live],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    scan = os.path.join(dtbdir, 'alioth-scan.txt')
    open(scan, 'w', encoding='utf-8').write(r.stdout)
    print(f'scan -> {scan}')
    tail = r.stdout.split('== Suggested')[-1] if '== Suggested' in r.stdout else ''
    print('== Suggested' + tail if tail else r.stdout[-2000:])
    print('\nDone. Keep the backup folder safe and out of git (it is in .gitignore).')


if __name__ == '__main__':
    main()
