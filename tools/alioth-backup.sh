#!/bin/bash
# Back up alioth's per-device partitions and pull the live device tree.
#
# Run with the phone in a recovery that gives adb root (OrangeFox or TWRP,
# booted temporarily with `fastboot boot recovery.img`). Read-only on the
# phone: it only reads partitions with dd.
#
#   tools/alioth-backup.sh [OUTDIR]      (default: backup/)
#
# persist, modemst1/2, fsg and fsc hold IMEI and calibration data that cannot
# be downloaded anywhere. Keep OUTDIR off git (.gitignore covers backup/ and dtb/).
set -euo pipefail
OUT=${1:-backup}
mkdir -p "$OUT" dtb

adb wait-for-device
name=$(adb shell getprop ro.product.device | tr -d '\r')
[ -z "$name" ] && name=$(adb shell getprop ro.build.product | tr -d '\r')
echo "device: ${name:-unknown}"
case "$name" in
	*alioth*|*aliothin*) ;;
	*) echo "warning: this does not look like alioth; continuing anyway" >&2 ;;
esac
adb shell 'id -u' | grep -q '^0' || { echo "error: adb is not root; use a recovery with root adb" >&2; exit 1; }

BYNAME=/dev/block/bootdevice/by-name
slot=$(adb shell getprop ro.boot.slot_suffix | tr -d '\r')
echo "active slot: ${slot:-none}"

pull() {
	local part=$1 dev
	for cand in "$part" "$part$slot" "${part}_a"; do
		if adb shell "[ -e $BYNAME/$cand ]"; then dev=$cand; break; fi
	done
	if [ -z "${dev:-}" ]; then echo "  skip $part (not found)"; return; fi
	echo "  $dev"
	adb exec-out "dd if=$BYNAME/$dev bs=1048576 2>/dev/null" > "$OUT/$dev.img"
	adb shell "sha256sum $BYNAME/$dev" | awk '{print $1}' > "$OUT/$dev.img.sha256.phone"
	sha256sum "$OUT/$dev.img" | awk '{print $1}' | cmp -s - "$OUT/$dev.img.sha256.phone" \
		|| { echo "error: checksum mismatch for $dev" >&2; exit 1; }
}

echo "partitions -> $OUT/"
for p in persist modemst1 modemst2 fsg fsc boot dtbo vbmeta vendor_boot; do pull "$p"; done

echo "live device tree -> dtb/alioth-live.dtb"
adb exec-out 'cat /sys/firmware/fdt' > dtb/alioth-live.dtb
adb shell 'cat /proc/cmdline' > dtb/alioth-cmdline.txt
adb shell 'cat /proc/iomem' > dtb/alioth-iomem.txt 2>/dev/null || true

echo
echo "next:"
echo "  python3 tools/unpack_bootv2.py $OUT/boot$slot.img dtb/boot_unpacked   # stock DTB for the shim"
echo "  python3 tools/fdt-scan.py dtb/alioth-live.dtb                         # values for tools/boards/alioth.py"
