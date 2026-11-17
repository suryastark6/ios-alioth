/*
 * Just enough flattened-device-tree parsing to find what ABL put in
 * /chosen (initrd location). Big-endian, 4-byte aligned tokens.
 */
#include "fdt.h"

#define FDT_MAGIC	0xd00dfeed
#define FDT_BEGIN_NODE	1
#define FDT_END_NODE	2
#define FDT_PROP	3
#define FDT_NOP		4
#define FDT_END		9

static uint32_t be32(uintptr_t a)
{
	return __builtin_bswap32(*(volatile uint32_t *)a);
}

static int streq(const char *a, const char *b)
{
	while (*a && *a == *b)
		a++, b++;
	return *a == *b;
}

static uintptr_t align4(uintptr_t a)
{
	return (a + 3) & ~3UL;
}

static uintptr_t skip_str(uintptr_t p)
{
	/* byte loads are fine on Device memory as long as they are aligned to 1 */
	while (*(volatile char *)p)
		p++;
	return p + 1;
}

int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out)
{
	if (!fdt || be32(fdt) != FDT_MAGIC)
		return 0;
	uintptr_t p = fdt + be32(fdt + 8);		/* off_dt_struct */
	uintptr_t strings = fdt + be32(fdt + 12);	/* off_dt_strings */
	int depth = 0, in_chosen = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			in_chosen = depth == 2 && streq(name, "chosen");
			p = align4(skip_str(p));
			break;
		}
		case FDT_END_NODE:
			if (in_chosen)
				return 0;
			depth--;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			if (in_chosen && streq((const char *)(strings + nameoff), prop)) {
				if (len == 4)
					*out = be32(val);
				else if (len == 8)
					*out = (uint64_t)be32(val) << 32 | be32(val + 4);
				else
					return 0;
				return 1;
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		default:	/* FDT_END or garbage */
			return 0;
		}
	}
}

static uint64_t be64(uintptr_t a)
{
	return (uint64_t)be32(a) << 32 | be32(a + 4);
}

static int starts_with(const char *s, const char *prefix)
{
	while (*prefix && *s == *prefix)
		s++, prefix++;
	return *prefix == 0 && (*s == 0 || *s == '@');
}

static int overlaps(uint64_t a, uint64_t an, uint64_t b, uint64_t bn)
{
	return a < b + bn && b < a + an;
}

int fdt_check_range(uintptr_t fdt, uint64_t base, uint64_t size,
		    uint64_t *bad_base, uint64_t *bad_size)
{
	if (!fdt || be32(fdt) != FDT_MAGIC || !size)
		return -1;
	/* /memreserve/ block: (address, size) pairs ending with (0, 0) */
	for (uintptr_t r = fdt + be32(fdt + 16); ; r += 16) {
		uint64_t a = be64(r), n = be64(r + 8);
		if (!a && !n)
			break;
		if (overlaps(base, size, a, n)) {
			*bad_base = a;
			*bad_size = n;
			return 2;
		}
	}
	uintptr_t p = fdt + be32(fdt + 8);
	uintptr_t strings = fdt + be32(fdt + 12);
	int depth = 0, in_mem = 0, in_rsv = 0, inside = 0, nodes = 0;
	int rsv_depth = 0;

	for (;;) {
		uint32_t tok = be32(p);
		p += 4;
		switch (tok) {
		case FDT_BEGIN_NODE: {
			const char *name = (const char *)p;
			depth++;
			if (depth == 2) {
				in_mem = starts_with(name, "memory");
				if (starts_with(name, "reserved-memory"))
					rsv_depth = 2;
			}
			in_rsv = rsv_depth && depth == rsv_depth + 1;
			p = align4(skip_str(p));
			nodes++;
			break;
		}
		case FDT_END_NODE:
			if (depth == 2) {
				in_mem = 0;
				rsv_depth = 0;
			}
			depth--;
			in_rsv = rsv_depth && depth == rsv_depth + 1;
			if (depth < 0)
				return -1;
			break;
		case FDT_PROP: {
			uint32_t len = be32(p), nameoff = be32(p + 4);
			uintptr_t val = p + 8;
			const char *pname = (const char *)(strings + nameoff);
			if ((in_mem || in_rsv) && streq(pname, "reg") && !(len % 16)) {
				for (uint32_t i = 0; i < len; i += 16) {
					uint64_t a = be64(val + i), n = be64(val + i + 8);
					if (in_mem && base >= a && base + size <= a + n)
						inside = 1;
					if (in_rsv && n && overlaps(base, size, a, n)) {
						*bad_base = a;
						*bad_size = n;
						return 2;
					}
				}
			}
			p = align4(val + len);
			break;
		}
		case FDT_NOP:
			break;
		case FDT_END:
			if (!nodes)
				return -1;
			return inside ? 0 : 1;
		default:
			return -1;
		}
	}
}
