"""POCO F3 / Redmi K40 / Mi 11X (alioth, SM8250-AC Snapdragon 870).

STATUS: NOT BOOTED YET. Values marked VERIFY are the SM8250 defaults from the
upstream Linux sm8250.dtsi and are expected to match, but must be checked
against YOUR phone's live FDT (/sys/firmware/fdt from recovery) with
    python3 tools/fdt-scan.py dtb/alioth-live.dtb
None = unknown; mkadt.py will not build an alioth ADT until it is filled in.
"""
BOARD = {
    'name': 'alioth',
    'soc': 'qcom,sm8250',
    'compatible': 'xiaomi,alioth',
    # Low option: unknown until reserved-memory is read from the live FDT.
    'phys_base': None,
    'mem_size': None,
    # alioth ships with 6 or 8 GiB. Pick the largest range in the memory node
    # (above 4 GiB, if possible) that no reserved-memory entry overlaps.
    'high_phys_base': None,
    'high_mem_size': None,
    'gicd': 0x17a00000, 'gicd_size': 0x10000,     # VERIFY (sm8250 intc@17a00000)
    'gicr': 0x17a60000, 'gicr_size': 0x100000,    # VERIFY
    'timebase': 19200000,                          # VERIFY (arm,armv8-timer)
    'vtimer_intid': 19,                            # VERIFY (GIC_PPI 3 -> INTID 19)
    # cont_splash / framebuffer reserved region. 0x9c000000 is common on
    # SM8250 phones; the size depends on the panel. Read it from the FDT.
    'fb': None, 'fb_size': None,
    'fb_w': 1080, 'fb_h': 2400,                    # VERIFY (6.67" 1080x2400 AMOLED)
    'ufs': 0x01d84000, 'ufs_size': 0x3000,        # VERIFY (sm8250 ufshc@1d84000)
    # Kryo 585: cores 0-3 Cortex-A55, 4-6 Cortex-A77, 7 Cortex-A77 prime.
    # MPIDR regs 0x000..0x700 as on sweet: VERIFY against /cpus/cpu@N reg.
    'cpus': [(c << 8, 'qcom,kryo585', 3187200000 if c == 7 else 2419200000 if c >= 4 else 1804800000)
             for c in range(8)],
    'ecid': 0x414c494f54480001,  # 'ALIOTH' + 1, synthetic (not the phone's)
}
