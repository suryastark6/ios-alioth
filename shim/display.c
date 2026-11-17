/*
 * Getting pixels onto a command-mode panel (alioth).
 *
 * sweet's panel runs in video mode: it scans the splash buffer by itself, so
 * anything written there appears. alioth's k11a AMOLED is a DSC command-mode
 * panel. It keeps showing its own internal frame until the display controller
 * (SDE/DPU at 0x0ae00000) sends a new one. ABL leaves that path configured for
 * its continuous splash: a source pipe fetching the buffer at FB_BASE, a layer
 * mixer, a pingpong with tear check, DSC, and INTF_1 (DSI0).
 *
 * Two ways to send frames, both straight from Xiaomi's display driver
 * (techpack/display/msm/sde, alioth-r-oss):
 *   - autorefresh: PP_AUTOREFRESH_CONFIG = BIT(31) | frame_count makes the
 *     pingpong send a frame on every Nth TE pulse without any further help.
 *     One CTL_START starts it. With it on, the XNU kernel's framebuffer
 *     writes show up with no kernel changes.
 *   - a kick per frame: CTL_START = 1 on the active CTL (what the driver's
 *     trigger_start does in command mode).
 * disp_init() reports what ABL left, turns autorefresh on and kicks once.
 * disp_present() kicks again when autorefresh did not take.
 *
 * Only register reads, the autorefresh register of the pingpong ABL already
 * uses, and CTL_START are written. Nothing is reconfigured.
 */
#include <stdint.h>
#include "board.h"
#include "console.h"
#include "display.h"

#if HAS_CMD_PANEL

#define CTL_TOP			0x014
#define CTL_FLUSH		0x018
#define CTL_START		0x01c
#define CTL_STATUS		0x064
#define CTL_DSC_ACTIVE		0x0e8
#define CTL_INTF_ACTIVE		0x0f4
#define PP_TEAR_CHECK_EN	0x000
#define PP_SYNC_CONFIG_VSYNC	0x004
#define PP_INT_COUNT_VAL	0x014	/* [31:16] TE (read pointer) frame count */
#define PP_LINE_COUNT		0x02c	/* write pointer: line of the frame being sent */
#define PP_AUTOREFRESH_CONFIG	0x030
#define INTF_FRAME_COUNT	0x0ac
#define INTF_STATUS		0x26c
#define AUTOREFRESH_EN		(1U << 31)
#define AUTOREFRESH_EVERY	1	/* frame on every TE pulse */
#define INTF_DSI0		1	/* INTF_1; CTL_INTF_ACTIVE bit */

#define SSPP_SRC_SIZE		0x00
#define SSPP_SRC0_ADDR		0x14
#define SSPP_SRC_YSTRIDE0	0x24
#define SSPP_SRC_FORMAT		0x30
static const uint32_t sspp_off[] = {
	0x5000, 0x7000, 0x9000, 0xb000, 0x25000, 0x27000, 0x29000, 0x2b000,
};

static int ctl = -1;		/* CTL driving DSI0 */
static int pp = -1;		/* pingpong with tear check on */
static int autorefresh;		/* 1: frames flow without kicks */
static uint64_t last_kick;

static inline uint32_t rd(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline void wr(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }

static uint64_t ticks(void)
{
	uint64_t t;
	__asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(t));
	return t;
}

static uint64_t ticks_per_ms(void)
{
	uint64_t f;
	__asm__ volatile("mrs %0, cntfrq_el0" : "=r"(f));
	return f / 1000;
}

static void wait_ms(unsigned ms)
{
	uint64_t end = ticks() + ticks_per_ms() * ms;
	while (ticks() < end)
		;
}

static void kick(void)
{
	/* Buffer writes (Device or Normal-NC) must land before the fetch starts. */
	__asm__ volatile("dsb sy" ::: "memory");
	wr(MDP_CTL(ctl) + CTL_START, 1);
	last_kick = ticks();
}

void disp_present(void)
{
	if (ctl < 0 || autorefresh)
		return;
	/* At most one frame per ~17 ms: let the previous transfer finish. */
	uint64_t due = last_kick + ticks_per_ms() * 17;
	while (ticks() < due)
		;
	kick();
}

/*
 * The console draws at FB_BASE (ABL's cont_splash_region). If exactly one
 * source pipe fetches a full-screen 1080x2400 buffer with our 4320-byte
 * stride from somewhere else (ABL's fastboot screen might), draw there.
 */
static void follow_scanout(void)
{
	uint32_t found = 0, n = 0;
	for (unsigned i = 0; i < sizeof(sspp_off) / sizeof(sspp_off[0]); i++) {
		uintptr_t s = MDP_BASE + sspp_off[i];
		uint32_t addr = rd(s + SSPP_SRC0_ADDR);
		if (!addr)
			continue;
		n++;
		if (rd(s + SSPP_SRC_SIZE) == ((uint32_t)FB_H << 16 | FB_W) &&
		    (rd(s + SSPP_SRC_YSTRIDE0) & 0xffff) == FB_STRIDE)
			found = addr;
	}
	if (n == 1 && found && found != (uint32_t)FB_BASE && found >= 0x80000000u)
		con_fb = (volatile uint32_t *)(uintptr_t)found;
}

const char *disp_init(void)
{
	follow_scanout();
	for (int i = 0; i < MDP_NUM_CTL && ctl < 0; i++)
		if (rd(MDP_CTL(i) + CTL_INTF_ACTIVE) & (1U << INTF_DSI0))
			ctl = i;
	for (int i = 0; i < MDP_NUM_PP && pp < 0; i++)
		if (rd(MDP_PP(i) + PP_TEAR_CHECK_EN) & 1)
			pp = i;
	if (ctl < 0)
		return "no CTL on DSI0: no splash path";

	/* Without a pingpong in tear-check mode, per-frame kicks are the only way. */
	if (pp >= 0) {
		uint32_t ar = rd(MDP_PP(pp) + PP_AUTOREFRESH_CONFIG);
		if (!(ar & AUTOREFRESH_EN))
			wr(MDP_PP(pp) + PP_AUTOREFRESH_CONFIG, AUTOREFRESH_EN | AUTOREFRESH_EVERY);
	}
	kick();
	if (pp < 0)
		return "kick mode (no tear-check pingpong)";

		/*
	 * Autorefresh works if frames keep going out with no further kicks: the
	 * write pointer line count cycles through each frame (the Xiaomi driver
	 * reads it the same way to tell whether a transfer is in progress).
	 * INTF_1's frame counter is a video-mode timing engine counter and need
	 * not move for a command-mode panel, so it is only reported.
	 */
	wait_ms(50);
	uint32_t first = rd(MDP_PP(pp) + PP_LINE_COUNT) & 0xffff, changes = 0;
	uint32_t te0 = rd(MDP_PP(pp) + PP_INT_COUNT_VAL) >> 16;
	for (int i = 0; i < 400; i++) {		/* 400 samples over ~200 ms */
		uint64_t next = ticks() + ticks_per_ms() / 2;
		while (ticks() < next)
			;
		uint32_t now = rd(MDP_PP(pp) + PP_LINE_COUNT) & 0xffff;
		if (now != first) {
			changes++;
			first = now;
		}
	}
	uint32_t te1 = rd(MDP_PP(pp) + PP_INT_COUNT_VAL) >> 16;
	autorefresh = changes >= 4;
	if (autorefresh)
		return "autorefresh on";
	/*
	 * Not sending by itself: switch autorefresh back off (the Xiaomi driver
	 * never kicks while it is on) and send a frame per draw instead.
	 */
	wr(MDP_PP(pp) + PP_AUTOREFRESH_CONFIG, 0);
	wait_ms(20);
	kick();
	return te1 != te0 ? "kick mode (TE ok, autorefresh idle)" : "kick mode (no TE seen)";
}

/* Report what ABL left, so the first boot answers the M2 questions. */
void disp_report(const char *mode)
{
	con_str("DISP", mode);
	con_hex2("DISP", "ctl=", (uint32_t)ctl, "pp=", (uint32_t)pp);
	if (ctl >= 0) {
		uintptr_t c = MDP_CTL(ctl);
		con_hex2("CTL", "top=", rd(c + CTL_TOP), "intf=", rd(c + CTL_INTF_ACTIVE));
		con_hex2("CTL", "dsc=", rd(c + CTL_DSC_ACTIVE), "status=", rd(c + CTL_STATUS));
		con_hex2("CTL", "flush=", rd(c + CTL_FLUSH), "start=", rd(c + CTL_START));
	}
	if (pp >= 0) {
		uintptr_t p = MDP_PP(pp);
		con_hex2("PP", "vsync=", rd(p + PP_SYNC_CONFIG_VSYNC), "autoref=", rd(p + PP_AUTOREFRESH_CONFIG));
		con_hex2("PP", "te/line=", rd(p + PP_INT_COUNT_VAL), "wrline=", rd(p + PP_LINE_COUNT));
	}
	con_hex2("INTF1", "frames=", rd(MDP_INTF(INTF_DSI0) + INTF_FRAME_COUNT),
		 "status=", rd(MDP_INTF(INTF_DSI0) + INTF_STATUS));
	/* Which pipe fetches the splash buffer, and in what layout. The console
	 * assumes a8r8g8b8 with a 4320-byte stride at FB_BASE. */
	for (unsigned i = 0; i < sizeof(sspp_off) / sizeof(sspp_off[0]); i++) {
		uintptr_t s = MDP_BASE + sspp_off[i];
		uint32_t addr = rd(s + SSPP_SRC0_ADDR);
		if (!addr)
			continue;
		con_hex2("SSPP", "off=", sspp_off[i], "addr=", addr);
		con_hex2("SSPP", "size=", rd(s + SSPP_SRC_SIZE), "stride=", rd(s + SSPP_SRC_YSTRIDE0));
		con_hex2("SSPP", "fmt=", rd(s + SSPP_SRC_FORMAT), "fb?=", addr == (uint32_t)FB_BASE);
	}
	con_hex("CONSOLE", (uintptr_t)con_fb);
}

#else	/* video-mode panel */

const char *disp_init(void) { return "video mode"; }
void disp_present(void) {}
void disp_report(const char *mode) { (void)mode; }

#endif
