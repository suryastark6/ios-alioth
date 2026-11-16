"""Redmi Note 10 Pro (sweet, SM7150): the values ios-sweet boots with."""
BOARD = {
    'name': 'sweet',
    'soc': 'qcom,sm7150',
    'compatible': 'xiaomi,sweet',
    # Kernel-managed RAM, low option: above every Qualcomm XPU carve-out
    'phys_base': 0xb0000000,
    'mem_size': 0x4d000000,
    # --highmem: the whole upper DDR bank. Live FDT memory node is
    # <0x80000000 2G>, <0x1_00000000 0xfcc00000>; every fixed reserved-memory
    # carve-out is in the low bank and the dynamic pools are limited below 4G.
    'high_phys_base': 0x100000000,
    'high_mem_size': 0xfcc00000,
    'gicd': 0x17a00000, 'gicd_size': 0x10000,
    'gicr': 0x17a60000, 'gicr_size': 0x100000,
    'timebase': 19200000,
    'vtimer_intid': 19,
    # ABL's continuous-splash framebuffer
    'fb': 0x9c000000, 'fb_size': 0x1700000,
    'fb_w': 1080, 'fb_h': 2400,
    'ufs': 0x01d84000, 'ufs_size': 0x3000,
    # One entry per physical core in MPIDR order: (MPIDR reg, core type, max Hz)
    'cpus': [(c << 8, 'qcom,kryo470', 2304000000 if c >= 6 else 1804800000) for c in range(8)],
    'ecid': 0x5357454554000001,  # 'SWEET' + 1, synthetic
}
