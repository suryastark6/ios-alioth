/* Per-phone physical addresses used by the shim.
 * Select with  BOARD=alioth ./build.sh ...  (default: sweet).
 * alioth values come from alioth's device tree source (docs/ALIOTH-HARDWARE.md)
 * and are NOT yet confirmed on a phone: check them against the live FDT
 * (tools/fdt-scan.py) on the first boot. */
#ifndef BOARD_H
#define BOARD_H

#if defined(BOARD_ALIOTH)
/* qcom,msm-imem@146bf000 restart_reason@65c */
#define IMEM_RESTART_REASON	0x146bf65cUL
#define PSHOLD			0x0c264000UL	/* restart@c264000 */
#define GICD_BASE		0x17a00000UL	/* interrupt-controller@17a00000 */
#define GICR_BASE		0x17a60000UL
#define GICR_SIZE		0x100000UL
#define UFS_BASE		0x01d84000UL	/* ufshc@1d84000 */
/* kona timer node: <GIC_PPI 13>, <14>, <11>, <12> (secure, non-secure phys,
 * virtual, hyp) -> virtual INTID 27, physical 30. NOT sweet's 19/18. */
#define VTIMER_INTID		27
#define PTIMER_INTID		30
/* Command-mode DSC panel (k11a_38_08_0a_dsc_cmd): pixels reach the panel only
 * when the display controller sends a frame, see display.c.
 * qcom,mdss_mdp@ae00000: sde-off 0x1000, ctl 0x2000 + 0x200*n (6),
 * pingpong 0x71000 + 0x800*n (6), intf 0x6b000 + 0x800*n (INTF_1 = DSI0),
 * sspp vig 0x5000/7000/9000/b000, dma 0x25000/27000/29000/2b000. */
#define HAS_CMD_PANEL		1
/* Refuse to start XNU unless its RAM range is inside a live /memory bank and
 * clear of every reserved region (the range is chosen before the phone's
 * memory node has been seen). */
#define CHECK_RAM		1
#define MDP_BASE		0x0ae00000UL
#define MDP_CTL(n)		(MDP_BASE + 0x2000UL + 0x200UL * (n))
#define MDP_NUM_CTL		6
#define MDP_PP(n)		(MDP_BASE + 0x71000UL + 0x800UL * (n))
#define MDP_NUM_PP		6
#define MDP_INTF(n)		(MDP_BASE + 0x6b000UL + 0x800UL * (n))
#else	/* sweet (SM7150), from the sweet live FDT */
#define IMEM_RESTART_REASON	0x146aa65cUL	/* qcom,msm-imem restart_reason@65c */
#define PSHOLD			0x0c264000UL
#define GICD_BASE		0x17a00000UL
#define GICR_BASE		0x17a60000UL
#define GICR_SIZE		0x100000UL
#define UFS_BASE		0x01d84000UL	/* ufshc@1d84000, sweet live FDT */
#define VTIMER_INTID		19	/* DT: <GIC_PPI 3 ...>, not the usual 27 */
#define PTIMER_INTID		18	/* DT: <GIC_PPI 2 ...> */
#define HAS_CMD_PANEL		0	/* video-mode panel: scans the buffer by itself */
#define CHECK_RAM		0	/* range measured on the phone: report only */
#endif

#endif
