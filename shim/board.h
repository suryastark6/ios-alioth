/* Per-phone physical addresses used by the shim.
 * Select with  BOARD=alioth ./build.sh ...  (default: sweet).
 * alioth values are the SM8250 defaults from the Linux sm8250.dtsi and are
 * NOT verified on a phone yet: check each against the live FDT
 * (tools/fdt-scan.py) before the first boot. */
#ifndef BOARD_H
#define BOARD_H

#if defined(BOARD_ALIOTH)
/* qcom,msm-imem@146bf000 restart_reason@65c (VERIFY: imem node + offset) */
#define IMEM_RESTART_REASON	0x146bf65cUL
#define PSHOLD			0x0c264000UL	/* restart@c264000 (VERIFY) */
#define GICD_BASE		0x17a00000UL	/* interrupt-controller@17a00000 (VERIFY) */
#define GICR_BASE		0x17a60000UL
#define GICR_SIZE		0x100000UL
#define UFS_BASE		0x01d84000UL	/* ufshc@1d84000 (VERIFY) */
#else	/* sweet (SM7150), from the sweet live FDT */
#define IMEM_RESTART_REASON	0x146aa65cUL	/* qcom,msm-imem restart_reason@65c */
#define PSHOLD			0x0c264000UL
#define GICD_BASE		0x17a00000UL
#define GICR_BASE		0x17a60000UL
#define GICR_SIZE		0x100000UL
#define UFS_BASE		0x01d84000UL	/* ufshc@1d84000, sweet live FDT */
#endif

#endif
