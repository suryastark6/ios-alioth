#!/bin/bash
# Build an alioth test image for one milestone of docs/ALIOTH-PLAN.md.
#
#   tools/build-alioth.sh m1 [--header 2|3] [--dtb DTB]
#   tools/build-alioth.sh m3 KERNEL [--cpus N] [--header 2|3] [--dtb DTB]
#   tools/build-alioth.sh m5 KERNEL [--cpus N] [--header 2|3] [--dtb DTB]
#
#   m1  shim only: display probe, payload check, read-only UFS probe, back to
#       fastboot after ~3 min (M1/M2)
#   m3  XNU with the alioth ADT, no root device: success = the kernel log
#       reaches "waiting for root device" on screen (M3/M4)
#   m5  XNU with root on userdata (rd=ufsroot0): needs the iOS root image
#       flashed to userdata first (M5)
#
# KERNEL: kernel.development.sweet from the xnu-kernel artifact of the
# GitHub Actions run. --header 3 (default) packs a boot image v3: ABL then
# takes the DTB from the phone's vendor_boot. --header 2 needs --dtb
# (dtb/boot_unpacked/dtb from tools/alioth-backup.py).
# Output: out/alioth-<milestone>-v<header>.img
set -euo pipefail
cd "$(dirname "$0")/.."

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[ $# -ge 1 ] || usage
M=$1; shift
KERNEL=
case "$M" in
	m1) ;;
	m3|m5) [ $# -ge 1 ] || usage; KERNEL=$1; shift
		[ -f "$KERNEL" ] || { echo "error: kernel $KERNEL not found" >&2; exit 1; } ;;
	*) usage ;;
esac
HEADER=3 DTB=dtb/boot_unpacked/dtb CPUS=1
while [ $# -gt 0 ]; do
	case "$1" in
		--header) HEADER=$2; shift 2 ;;
		--dtb) DTB=$2; shift 2 ;;
		--cpus) CPUS=$2; shift 2 ;;
		*) usage ;;
	esac
done
case "$CPUS" in [1-8]) ;; *) echo "error: --cpus 1-8" >&2; exit 1 ;; esac
if [ "$HEADER" = 2 ] && [ ! -f "$DTB" ]; then
	echo "error: --header 2 needs the phone's DTB ($DTB): run tools/alioth-backup.py" >&2; exit 1
fi
mkdir -p out shim/out
OUT=out/alioth-$M-v$HEADER.img

# Common boot-args (see docs/SWEET-README.md). wdt=-1: no watchdog;
# -enable_kprintf_spam + no sweetfb_noconsole: kernel log on the panel.
ARGS="debug=0xc serial=3 cpus=$CPUS keepsyms=1 -enable_kprintf_spam -noprogress wdt=-1"
case "$M" in
	m1)
		PAYLOAD= ;;
	m3)
		PAYLOAD=shim/out/payload.bin ;;
	m5)
		PAYLOAD=shim/out/payload.bin
		ARGS="$ARGS rd=ufsroot0 ufsrw=1 rootrw=1 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin launchd_unsecure_cache=1 sweetfb_hz=30" ;;
esac

if [ -n "$PAYLOAD" ]; then
	python3 tools/mkadt.py shim/out/alioth.adt --board alioth --highmem
	python3 tools/mkpayload.py "$KERNEL" shim/out/alioth.adt "$PAYLOAD" --cmdline "$ARGS"
fi
(cd shim && BOARD=alioth HEADER="$HEADER" DTB="$(cd .. && realpath -m "$DTB")" ./build.sh ${PAYLOAD:+"../$PAYLOAD"} >/dev/null)
cp shim/out/shim-boot.img "$OUT"
echo "$OUT  ($(stat -c %s "$OUT") bytes)"
[ -n "$PAYLOAD" ] && echo "boot-args: $ARGS"
echo "test:  fastboot boot $OUT"
