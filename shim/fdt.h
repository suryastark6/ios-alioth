#pragma once
#include <stdint.h>

/* Read a u32/u64 (cell-size agnostic) property of /chosen. Returns 0 if absent. */
int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out);

/*
 * Check that [base, base + size) lies inside one /memory bank and overlaps no
 * /reserved-memory reg, /memreserve/ entry. Returns 0 if it is safe;
 * otherwise 1 (not inside a memory bank), 2 (overlaps a reserved region,
 * returned in *bad_base and *bad_size) or -1 (DTB not understood).
 * Assumes #address-cells = #size-cells = 2 at the root and in
 * /reserved-memory, as on Qualcomm phones.
 */
int fdt_check_range(uintptr_t fdt, uint64_t base, uint64_t size,
		    uint64_t *bad_base, uint64_t *bad_size);
