"""POCO F3 / Redmi K40 / Mi 11X (alioth, SM8250-AC Snapdragon 870).

STATUS: NOT BOOTED YET. Values marked SRC come from alioth's own device tree
source (LineageOS android_kernel_xiaomi_sm8250: kona-v2.1.dtb +
alioth-sm8250-overlay.dtbo, see docs/ALIOTH-HARDWARE.md). They still need a
check against YOUR phone's live FDT (/sys/firmware/fdt from recovery):
    python3 tools/fdt-scan.py dtb/alioth-live.dtb
None = only the live FDT can tell (ABL fills in the memory node at boot);
mkadt.py will not build an alioth ADT until it is filled in.
"""
BOARD = {
    'name': 'alioth',
    'soc': 'qcom,sm8250',
    'compatible': 'xiaomi,alioth',
    # Low option: none known to be safe. The source has fixed carve-outs up to
    # 0x9e400000 plus disp_rdump_region at 0xb0400000 (+16M), which overlaps
    # sweet's low choice of 0xb0000000. Use --highmem.
    'phys_base': None,
    'mem_size': None,
    # Every fixed carve-out is below 4 GiB and every dynamic pool's
    # alloc-ranges ends at 0xffffffff (SRC), so XNU goes above 4 GiB.
    # LIVE (8 GB aliothin, NOTES.md M0): ABL's /memory banks are
    # 0x80000000 +0x3bb00000, 0xc0000000 +0xc0000000 and
    # 0x180000000 +0x100000000. The earlier 0x100000000 +3 GiB ran across the
    # 0x180000000 bank edge, which the shim's one-bank check rejects
    # (shim/fdt.c fdt_check_range, CHECK_RAM). 0x180000000 +3 GiB lies inside
    # the 4 GiB bank and clear of every reserved region (no reserved-memory
    # node above 4 GiB). A 6 GB phone has a different top bank: scan it first.
    'high_phys_base': 0x180000000,
    'high_mem_size': 0xc0000000,
    'gicd': 0x17a00000, 'gicd_size': 0x10000,     # SRC interrupt-controller@17a00000
    'gicr': 0x17a60000, 'gicr_size': 0x100000,    # SRC
    'timebase': 19200000,                          # SRC timer clock-frequency
    # SRC timer interrupts <PPI 13>, <14>, <11>, <12>: virtual = PPI 11 =
    # INTID 27. NOT sweet's 19 (Qualcomm's SM7150 tree numbers them 1/2/3/0).
    'vtimer_intid': 27,
    # SRC cont_splash_region@9c000000; panel k11a_38_08_0a_dsc_cmd is
    # 1080x2400, 24 bpp, DSC, COMMAND mode (shim/display.c sends the frames).
    'fb': 0x9c000000, 'fb_size': 0x2300000,
    'fb_w': 1080, 'fb_h': 2400,
    'ufs': 0x01d84000, 'ufs_size': 0x3000,        # SRC ufshc@1d84000
    # Kryo 585: cores 0-3 Cortex-A55, 4-6 Cortex-A77, 7 Cortex-A77 prime.
    # SRC MPIDR regs 0x000..0x700 (cpu@0..cpu@700), as on sweet.
    # The compatible stays 'qcom,kryo470': it is the IONameMatch key of the
    # kernel's boot CPU driver and AppleKeyStore stand-in (patches 0018,
    # 0038), not a description of the core. With 'qcom,kryo585' the CPU
    # driver never attaches and boot stops after "ATM subsystem is
    # initialized" (found in QEMU, tools/qemu-sweet.py).
    'cpus': [(c << 8, 'qcom,kryo470', 3187200000 if c == 7 else 2419200000 if c >= 4 else 1804800000)
             for c in range(8)],
    # SRC gpio-keys vol_up = <&pm8150_gpios 6 GPIO_ACTIVE_LOW>: PM8150 (SID 0)
    # GPIO6, block 0xc000 + 0x100 * 5. Power and volume-down are on the PON
    # block at SID 0 0x800 as on sweet. Read by patch 0082 from /sweet-keys.
    'volup_ppid': 0x0c5, 'volup_base': 0xc500,
    # SRC reserved-memory@80860000 (qcom,cmd-db): RPMh command database,
    # read by sweet_rpmh.c (patch 0086) to vote the touch rails.
    'rpmh_cmd_db': (0x80860000, 0x20000),
    'ecid': 0x414c494f54480001,  # 'ALIOTH' + 1, synthetic (not the phone's)
}
