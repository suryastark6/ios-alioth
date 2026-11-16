#pragma once
/* Frames for a command-mode panel (display.c); no-ops on video-mode boards. */
const char *disp_init(void);		/* call before drawing; returns the mode */
void disp_present(void);		/* after drawing: send a frame if needed */
void disp_report(const char *mode);	/* print what ABL left in the display path */
