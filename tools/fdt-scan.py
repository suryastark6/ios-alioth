#!/usr/bin/env python3
"""Print every value the port needs from a phone's live flattened device tree.

    python3 tools/fdt-scan.py dtb/alioth-live.dtb [--board-snippet]

Get the live tree from a running recovery (it is the tree ABL actually
booted with, after dtbo overlays):  tools/alioth-backup.sh
No dependencies; reads the DTB directly.
"""
import struct
import sys

FDT_MAGIC = 0xd00dfeed
BEGIN, END, PROP, NOP, FEND = 1, 2, 3, 4, 9
GIB4 = 1 << 32
ALIGN = 0x4000  # 16K pages


class Node:
    def __init__(self, name, parent):
        self.name, self.parent, self.props, self.children = name, parent, {}, []

    @property
    def path(self):
        if self.parent is None:
            return '/'
        p = self.parent.path
        return (p if p != '/' else '') + '/' + self.name

    def cells(self, key, default):
        v = self.props.get(key)
        return struct.unpack('>I', v)[0] if v and len(v) == 4 else default

    def str(self, key):
        v = self.props.get(key)
        return v.rstrip(b'\0').decode(errors='replace') if v is not None else None

    def strs(self, key):
        v = self.props.get(key)
        return [s.decode(errors='replace') for s in v.split(b'\0') if s] if v else []

    def u32s(self, key):
        v = self.props.get(key) or b''
        return list(struct.unpack('>%dI' % (len(v) // 4), v[:len(v) // 4 * 4]))

    def regs(self):
        """(addr, size) pairs using the parent's #address-cells/#size-cells."""
        par = self.parent
        ac = par.cells('#address-cells', 2) if par else 2
        sc = par.cells('#size-cells', 1) if par else 1
        w = self.u32s('reg')
        out, step = [], ac + sc
        for i in range(0, len(w) - step + 1, step):
            a = 0
            for x in w[i:i + ac]:
                a = (a << 32) | x
            s = 0
            for x in w[i + ac:i + step]:
                s = (s << 32) | x
            out.append((a, s))
        return out

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def parse(blob):
    magic, total, off_struct, off_strings = struct.unpack('>IIII', blob[:16])
    if magic != FDT_MAGIC:
        raise SystemExit('not a flattened device tree (bad magic)')
    strings = blob[off_strings:]
    pos, root, cur = off_struct, None, None
    while True:
        (tok,) = struct.unpack('>I', blob[pos:pos + 4])
        pos += 4
        if tok == BEGIN:
            end = blob.index(b'\0', pos)
            name = blob[pos:end].decode(errors='replace')
            pos = (end + 4) & ~3
            n = Node(name, cur)
            if cur is None:
                root = n
            else:
                cur.children.append(n)
            cur = n
        elif tok == END:
            cur = cur.parent
        elif tok == PROP:
            ln, nameoff = struct.unpack('>II', blob[pos:pos + 8])
            pos += 8
            key = strings[nameoff:strings.index(b'\0', nameoff)].decode()
            cur.props[key] = blob[pos:pos + ln]
            pos = (pos + ln + 3) & ~3
        elif tok == NOP:
            continue
        elif tok == FEND:
            return root
        else:
            raise SystemExit(f'bad FDT token {tok:#x} at {pos - 4:#x}')


def compat(n, *needles):
    c = ' '.join(n.strs('compatible')).lower()
    return any(x in c for x in needles)


def hx(v):
    return f'{v:#x}'


def section(t):
    print(f'\n== {t} ==')


def free_ranges(banks, reserved):
    """Subtract reserved ranges from memory banks; 16K-aligned pieces."""
    out = []
    for base, size in banks:
        pieces = [(base, base + size)]
        for rb, rs in reserved:
            nxt = []
            for a, b in pieces:
                if rb + rs <= a or rb >= b:
                    nxt.append((a, b))
                    continue
                if rb > a:
                    nxt.append((a, rb))
                if rb + rs < b:
                    nxt.append((rb + rs, b))
            pieces = nxt
        for a, b in pieces:
            a2 = (a + ALIGN - 1) & ~(ALIGN - 1)
            b2 = b & ~(ALIGN - 1)
            if b2 > a2:
                out.append((a2, b2 - a2))
    return sorted(out, key=lambda r: -r[1])


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = parse(open(sys.argv[1], 'rb').read())
    nodes = list(root.walk())
    found = {}
    phandles = {}
    for n in nodes:
        for key in ('phandle', 'linux,phandle'):
            if len(n.props.get(key, b'')) == 4:
                phandles[n.u32s(key)[0]] = n

    def ref(cells):
        """'<node path> + args' for a phandle reference list such as a gpio."""
        if not cells:
            return '-'
        target = phandles.get(cells[0])
        return f'{target.path if target else hex(cells[0])} {cells[1:]}'

    section('Identity')
    print('model:', root.str('model'))
    print('compatible:', ', '.join(root.strs('compatible')))
    chosen = next((n for n in root.children if n.name == 'chosen'), None)
    bootargs = chosen.str('bootargs') if chosen else None
    if bootargs:
        disp = [a for a in bootargs.split() if 'dsi_display' in a or 'mdss_mdp.panel' in a]
        print('panel selected by ABL:', ', '.join(disp) or '(not in bootargs)')

    section('Memory (step 3: dram-base / dram-size)')
    banks = []
    for n in nodes:
        if n.str('device_type') == 'memory':
            for a, s in n.regs():
                banks.append((a, s))
                print(f'  bank {hx(a)} size {hx(s)} ({s / GIB4 * 4:.2f} GiB)  [{n.path}]')
    reserved = []
    rm = next((n for n in root.children if n.name == 'reserved-memory'), None)
    if rm:
        print(f'  reserved-memory: {len(rm.children)} entries')
        for c in rm.children:
            regs = c.regs()
            tag = ' no-map' if 'no-map' in c.props else ''
            if regs:
                for a, s in regs:
                    reserved.append((a, s))
                    print(f'    {hx(a):>14} +{hx(s):<12} {c.name}{tag}')
            else:
                print(f'    {"dynamic":>14}  {"":<13} {c.name}{tag} '
                      f'(size {hx(c.regs()[0][1]) if c.regs() else c.u32s("size")}, '
                      f'alloc-ranges {c.u32s("alloc-ranges")})')
    free = free_ranges(banks, reserved)
    high = [r for r in free if r[0] >= GIB4]
    low = [r for r in free if r[0] < GIB4]
    if free:
        print('  largest free ranges (16K aligned):')
        for a, s in free[:5]:
            print(f'    {hx(a)} size {hx(s)} ({s / (1 << 20):.0f} MiB)')
    if high:
        found['high_phys_base'], found['high_mem_size'] = high[0]
    if low:
        found['phys_base'], found['mem_size'] = low[0]
    print('  NOTE: dynamic pools (no reg) can land anywhere in their alloc-ranges; keep clear of them.')

    section('Framebuffer (step 2: early console)')
    for n in nodes:
        nm = n.name.lower()
        if ('splash' in nm or 'framebuffer' in nm or 'display' in nm and n.parent is rm) and n.regs():
            for a, s in n.regs():
                print(f'  {n.path}: {hx(a)} size {hx(s)}')
                if 'splash' in nm and 'fb' not in found:
                    found['fb'], found['fb_size'] = a, s
    chosen_panel = None
    if bootargs and 'dsi_display0=' in bootargs:
        chosen_panel = bootargs.split('dsi_display0=')[1].split(':')[0].split()[0]
    panels = [n for n in nodes if n.str('qcom,mdss-dsi-panel-type')]
    if chosen_panel and not any(chosen_panel in (n.name, 'qcom,' + n.name) for n in panels):
        print(f'  (no panel node named {chosen_panel}; listing all)')
        chosen_panel = None
    for n in panels:
        if chosen_panel and chosen_panel not in (n.name, 'qcom,' + n.name):
            continue
        t = n.str('qcom,mdss-dsi-panel-type')
        sizes, dsc = set(), False
        for sub in n.walk():
            w = sub.u32s('qcom,mdss-dsi-panel-width')
            h = sub.u32s('qcom,mdss-dsi-panel-height')
            fr = sub.u32s('qcom,mdss-dsi-panel-framerate')
            if w and h:
                sizes.add(f'{w[0]}x{h[0]}@{fr[0] if fr else "?"}')
            dsc |= sub.str('qcom,compression-mode') == 'dsc'
        print(f'  panel {n.name}: {t}{" DSC" if dsc else ""} {", ".join(sorted(sizes)) or "?"}'
              f'{"  <- selected by ABL" if chosen_panel else ""}')
    if not chosen_panel and len(panels) > 1:
        print(f'  ({len(panels)} panel nodes; the live FDT\'s bootargs name the one in use)')
    print('  dsi_cmd_mode = command-mode panel: needs a refresh kick (see docs/ALIOTH-PLAN.md, M2).')

    section('Interrupt controller and timer (step 3)')
    for n in nodes:
        if compat(n, 'arm,gic-v3'):
            r = n.regs()
            print(f'  {n.path}: ' + ', '.join(f'{hx(a)}+{hx(s)}' for a, s in r))
            if len(r) >= 2:
                found['gicd'], found['gicd_size'] = r[0]
                found['gicr'], found['gicr_size'] = r[1]
        if compat(n, 'arm,armv8-timer'):
            w = n.u32s('interrupts')
            ppis = [w[i + 1] for i in range(0, len(w) - 2, 3) if w[i] == 1]
            print(f'  timer {n.path}: PPIs {ppis} -> INTIDs {[16 + p for p in ppis]} '
                  '(order: secure phys, non-secure phys, virtual, hyp)')
            if len(ppis) >= 3:
                found['vtimer_intid'] = 16 + ppis[2]
            f = n.u32s('clock-frequency')
            if f:
                found['timebase'] = f[0]
                print(f'  clock-frequency {f[0]}')

    section('CPUs (step 4)')
    cpus = next((n for n in root.children if n.name == 'cpus'), None)
    cpu_list = []
    if cpus:
        for c in cpus.children:
            if c.str('device_type') == 'cpu':
                r = c.u32s('reg')
                mpidr = r[-1] if r else None
                cpu_list.append(mpidr)
                print(f'  {c.name}: reg {hx(mpidr) if mpidr is not None else "?"} '
                      f'{", ".join(c.strs("compatible"))} capacity {c.u32s("capacity-dmips-mhz")}')
    for n in nodes:
        if n.name == 'psci' or compat(n, 'arm,psci'):
            print(f'  psci: method {n.str("method")}')

    section('Storage, reset, USB (steps 1 and 5)')
    for n in nodes:
        if compat(n, 'ufshc') and n.regs():
            print(f'  ufs {n.path}: {hx(n.regs()[0][0])}+{hx(n.regs()[0][1])}')
            found.setdefault('ufs', n.regs()[0][0])
        if compat(n, 'qcom,pshold') and n.regs():
            print(f'  pshold {n.path}: {hx(n.regs()[0][0])}')
        if compat(n, 'qcom,msm-imem') and n.regs():
            base = n.regs()[0][0]
            for c in n.children:
                if 'restart_reason' in c.name and c.u32s('reg'):
                    print(f'  imem restart_reason: {hx(base + c.u32s("reg")[0])} (shim IMEM_RESTART_REASON)')
        if compat(n, 'snps,dwc3') and n.regs():
            print(f'  dwc3 {n.path}: {hx(n.regs()[0][0])}')
        if compat(n, 'qcom,dwc-usb3', 'qcom,sm8250-dwc3') and n.regs():
            print(f'  usb wrapper {n.path}: ' + ', '.join(hx(a) for a, s in n.regs()))

    section('Touch (step 7)')
    touch_words = ('touch', 'goodix', 'focaltech', 'fts', 'novatek', 'nt36', 'synaptics', 'gt9', 'xiaomi,ts')
    for n in nodes:
        c = ' '.join(n.strs('compatible')).lower()
        if any(w in c for w in touch_words) and n.str('status') != 'disabled':
            bus = n.parent
            print(f'  {n.path}: {", ".join(n.strs("compatible"))}')
            print(f'    bus {bus.name} ({", ".join(bus.strs("compatible"))}) '
                  f'reg {[hx(a) for a, s in bus.regs()]} status {bus.str("status")}')
            print(f'    device reg {n.u32s("reg")} spi-max-frequency {n.u32s("spi-max-frequency")}')
            for k in sorted(n.props):
                if 'gpio' in k or 'supply' in k or 'irq' in k:
                    print(f'    {k}: {ref(n.u32s(k))}')

    section('Buttons (step 7)')
    pon_types = {0: 'KPDPWR (power)', 1: 'RESIN', 2: 'CBLPWR', 3: 'KPDPWR+RESIN'}
    for n in nodes:
        if compat(n, '-pon', 'qcom,qpnp-power-on', 'qcom,pm8941-pwrkey', 'qcom,pm8941-resin',
                  'gpio-keys') and n.str('status') != 'disabled':
            keys = [c for c in n.children if c.u32s('linux,code')]
            if not keys:
                continue
            # SPMI PMIC nodes have reg = <SID 0>; the PON block's reg is its offset.
            pmic = n.parent
            sid = pmic.u32s('reg')[0] if pmic and pmic.u32s('reg') else None
            print(f'  {n.path}: {", ".join(n.strs("compatible"))} reg {[hx(x) for x in n.u32s("reg")]}'
                  f'{f" (PMIC SID {sid})" if sid is not None and compat(n, "power-on", "-pon") else ""}')
            for c in keys:
                code = c.u32s('linux,code')[0]
                pt = c.u32s('qcom,pon-type')
                what = f' pon-type {pon_types.get(pt[0], pt[0])}' if pt else f' gpios {ref(c.u32s("gpios"))}'
                print(f'    {c.name}: linux,code {code} '
                      f'({ {114: "VOLUMEDOWN", 115: "VOLUMEUP", 116: "POWER"}.get(code, "?") }){what}')

    section('Suggested tools/boards/alioth.py values (check each by hand)')
    for k in ('phys_base', 'mem_size', 'high_phys_base', 'high_mem_size', 'fb', 'fb_size',
              'gicd', 'gicd_size', 'gicr', 'gicr_size', 'timebase', 'vtimer_intid', 'ufs'):
        v = found.get(k)
        print(f"    '{k}': {hx(v) if isinstance(v, int) and k not in ('timebase', 'vtimer_intid') else v},")
    if cpu_list:
        print(f"    # MPIDRs: {[hx(m) for m in cpu_list if m is not None]}")


if __name__ == '__main__':
    main()
