#!/usr/bin/env python3
import sys, os, math, time, signal, subprocess, shutil
import threading, termios, tty
try:
    import numpy as np
except ImportError:
    sys.exit("numpy is required:\n  pip install numpy --break-system-packages")

# ─── ANSI helpers ─────────────────────────────────────────────────────────────
HIDE  = '\033[?25l'
SHOW  = '\033[?25h'
HOME  = '\033[H'
CLR   = '\033[2J\033[H'
RST   = '\033[0m'
BOLD  = '\033[1m'

def rgb(r, g, b):  return f'\033[38;2;{r};{g};{b}m'

# ── THEME ────────────────────────────────────────────────────────────────────
# Change just this one line to retheme the whole logo. (R, G, B), 0-255.
THEME_COLOR = (25, 200, 160)   # greenish-blue / teal

def _lerp3(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def _lighten(c, amt):
    return tuple(int(v + (255 - v) * amt) for v in c)

def _darken(c, amt):
    return tuple(max(0, int(v * (1 - amt))) for v in c)

# Face: dim/dark version of the theme color up to a lightened highlight
_FACE_DARK   = _darken(THEME_COLOR, 0.90)
_FACE_BRIGHT = _lighten(THEME_COLOR, 0.35)

# Edge (extrusion sides): darker & less saturated than the face
_EDGE_DARK   = _darken(THEME_COLOR, 0.94)
_EDGE_BRIGHT = _darken(THEME_COLOR, 0.20)

def _face_lut(n=256):
    return [rgb(*_lerp3(_FACE_DARK, _FACE_BRIGHT, i / (n - 1))) for i in range(n)]

def _edge_lut(n=256):
    return [rgb(*_lerp3(_EDGE_DARK, _EDGE_BRIGHT, i / (n - 1))) for i in range(n)]

FACE_LUT = _face_lut()
EDGE_LUT = _edge_lut()

def face_col(b: float) -> str:
    return FACE_LUT[min(255, max(0, round(b * 255)))]

def edge_col(b: float) -> str:
    return EDGE_LUT[min(255, max(0, round(b * 255)))]

_LOGO_RAW = [
    "         _,met$$$$$gg.     ",
    "      ,g$$$$$$$$$$$$$$$P.  ",
    '    ,g$$P"     """Y$$.".   ',
    "   ,$$P'              `$$$.",
    "  ',$$P       ,ggs.     `$$b",
    "  `d$$'     ,$P\"'   .    $$$",
    "   $$P      d$'     ,    $$P",
    "   $$:      $.   -    ,d$$' ",
    "   $$;      Y$b._   _,d$P' ",
    "   Y$$.    `.`\"Y$$$$P\"'    ",
    "   `$$b      \"-.__         ",
    "    `Y$$b                  ",
    "     `Y$$.                 ",
    "       `$$b.               ",
    "         `Y$$b.            ",
    "            `\"Y$b._        ",
    "                `\"\"\"       ",
]

_LOGO_RAW=[
"                  -`                   ",
"                 .o+`                  ",
"                `ooo/                  ",
"               `+oooo:                 ",
"              `+oooooo:                ",
"              -+oooooo+:               ",
"            `/:-:++oooo+:              ",
"           `/++++/+++++++:             ",
"          `/++++++++++++++:            ",
"         `/+++ooooooooooooo/`          ",
"        ./ooosssso++osssssso+`         ",
"       .oossssso-````/ossssss+`        ",
"      -osssssso.      :ssssssso.       ",
"     :osssssss/        osssso+++.      ",
"    /ossssssss/        +ssssooo/-      ",
"  `/ossssso+/:-        -:/+osssso+-    ",
" `+sso+:-`                 `.-/+oso:   ", 
"`++:.                           `-/+/  ", 
".`                                 `/  "]

LW   = max(len(r) for r in _LOGO_RAW)
LOGO = [r.ljust(LW) for r in _LOGO_RAW]
LH   = len(LOGO)

logo_arr  = np.array([list(row) for row in LOGO], dtype='U1')   # [LH, LW]
logo_mask = logo_arr != ' '                                       # [LH, LW]


THICK     = 0.09      # extrusion half-thickness in normalised x-units
EDGE_SOFT = 0.06      # |cos a| below this → edge-on silhouette mode

# Light direction (upper-right-front, unit vector)
_LV  = np.array([0.50, -0.30, 0.812])
_LV /= float(np.linalg.norm(_LV))
LX, LZ = float(_LV[0]), float(_LV[2])

# Screen column grid (constant): px ∈ [-1, 1] across LW columns
PX_1D = np.linspace(-1.0, 1.0, LW, dtype=np.float64)   # [LW]

N_SAMP = 5    # side-wall sample points between front and back face

def _to_col(x_norm: np.ndarray) -> np.ndarray:
    """Normalised x ∈ [-1,1]  →  logo column index [0, LW-1]  (vectorised)."""
    return np.clip(
        np.rint((x_norm + 1.0) * 0.5 * (LW - 1)).astype(np.int32),
        0, LW - 1,
    )

def _in_range(x_norm: np.ndarray) -> np.ndarray:
    return (x_norm >= -1.0) & (x_norm <= 1.0)


def render(angle: float) -> list[str]:
    ca = math.cos(angle)
    sa = math.sin(angle)
    safe_ca = ca if abs(ca) >= 1e-6 else math.copysign(1e-6, ca)

    edge_on      = abs(ca) < EDGE_SOFT
    front_closer = ca > 0

    x_front = (PX_1D - THICK * sa) / safe_ca   # [LW]
    x_back  = (PX_1D + THICK * sa) / safe_ca   # [LW]

    fc  = _to_col(x_front)    # front face column lookup
    bcf = _to_col(x_back)     # back face: x_obj as-is (appears mirrored on screen, correct for back)

    front_in = _in_range(x_front)
    back_in  = _in_range(x_back)

    # ── Lighting ──────────────────────────────────────────────────────────
    eb = 0.38 + 0.42 * abs(sa)
    fb = 0.1 + 0.9 * abs(ca)   # bright face-on, dim edge-on
    bb = fb                        # same ramp for back face


    # ── Side-wall geometry ────────────────────────────────────────────────
    show_sides = abs(sa) > 0.08 and not edge_on
    wall_left  = (sa > 0) == front_closer  # flip side when back face is visible
    # Physical width of visible extrusion edge in screen columns
    n_wall = max(1, round(LW * THICK * abs(sa))) if show_sides else 0

    rows = []
    for r in range(LH):
        row_mask = logo_mask[r]

        f_hit   = front_in & row_mask[fc]
        b_hit   = back_in  & row_mask[bcf]
        visible = f_hit if front_closer else b_hit   # cols that show logo char

        # Build per-row side-wall mask at EVERY silhouette edge (both the
        # outer boundary and any inner gaps, e.g. the underside of the
        # arch between its two legs), not just the outermost edge.
        s_hit = np.zeros(LW, dtype=bool)
        if show_sides:
            hit_idx = np.where(visible)[0]
            if len(hit_idx) > 0:
                splits = np.where(np.diff(hit_idx) > 1)[0] + 1
                runs = np.split(hit_idx, splits)
                for run in runs:
                    if wall_left:
                        edge = int(run[0])
                        for c in range(max(0, edge - n_wall), edge):
                            s_hit[c] = True
                    else:
                        edge = int(run[-1])
                        for c in range(edge + 1, min(LW, edge + n_wall + 1)):
                            s_hit[c] = True

        buf = []
        for c in range(LW):
            px = float(PX_1D[c])

            if edge_on:
                if np.any(row_mask) and abs(px) <= THICK * abs(sa) + 0.025:
                    buf.append(edge_col(eb) + ',')
                else:
                    buf.append(' ')
                continue

            if bool(visible[c]):
                col_idx    = int(fc[c]) if front_closer else int(bcf[c])
                brightness = fb if front_closer else bb
                buf.append(face_col(brightness) + logo_arr[r, col_idx])
            elif bool(s_hit[c]):
                buf.append(edge_col(eb) + ',')
            else:
                buf.append(' ')

        rows.append(''.join(buf) + RST)

    return rows

# ─── system info ──────────────────────────────────────────────────────────────
def sysinfo() -> list[str]:
    R = BOLD + rgb(*THEME_COLOR); r0 = rgb(*THEME_COLOR); N = RST
    if shutil.which('fastfetch'):
        try:
            p = subprocess.run(
                ['fastfetch', '--logo', 'none',
                 '--color-keys', '1;36', '--color-separator', '0;36'],
                capture_output=True, text=True, timeout=8,
            )
            out=p.stdout.splitlines()
            for i in range(len(out)):
                if ":" in out[i]:
                    out[i]=R+out[i].split(":")[0]+N+':'+out[i].split(":")[-1]
                elif "@" in out[i]:
                    out[i]=R+out[i].split("@")[0]+N+'@'+R+out[i].split("@")[-1]+N
            return out
        except Exception:
            pass

    def sh(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return '?'
    user = os.environ.get('USER', sh('whoami'))
    host = sh('hostname -s')
    return [
        f'{BOLD}{R}{user}{N}@{BOLD}{R}{host}{N}',
        r0 + '─' * (len(user) + 1 + len(host)) + N,
        f'{R}OS      {N}  ' + sh("grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'"),
        f'{R}Kernel  {N}  ' + sh('uname -r'),
        f'{R}Uptime  {N}  ' + sh("uptime -p 2>/dev/null | sed 's/up //'"),
        f'{R}Shell   {N}  ' + os.environ.get('SHELL', '?'),
        f'{R}CPU     {N}  ' + sh("grep 'model name' /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2 | xargs"),
        f'{R}Memory  {N}  ' + sh("free -h 2>/dev/null | awk '/Mem:/{print $3\"/\"$2}'"),
        f'{R}Disk    {N}  ' + sh('df -h / 2>/dev/null | awk \'NR==2{print $3"/"$2" ("$5")"}\''),
    ]


# ─── main loop ────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    once = '--once' in args
    fps  = 18
    for i, a in enumerate(args):
        if a == '--fps' and i + 1 < len(args):
            try: fps = max(1, min(120, int(args[i + 1])))
            except ValueError: pass

    info = sysinfo()

    sys.stdout.write(HIDE + CLR)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old=termios.tcgetattr(fd)

    def bye(*_):
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(SHOW + RST + "\033[D" + '\r')
        os._exit(0)

    def _watch_input():
        try:
            tty.setcbreak(fd)
            k=sys.stdin.read(1)   # blocks until any key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(SHOW + RST + "\033[D" + k + '\r')
        os._exit(0)

    signal.signal(signal.SIGINT,  bye)
    signal.signal(signal.SIGTERM, bye)

    STEPS = 72
    step  = 2.0 * math.pi / STEPS
    angle = 0.0
    spins = 0

    LOGO_W = ' ' * LW   # blank logo row: same visual width as a real logo row

    result = subprocess.check_output(['bash', '-i', '-c', 'echo "${PS1@P}"'], stderr=subprocess.PIPE, text=True, encoding='utf-8')
    prompt = result.strip().split('\n')[-1]#+" █"

    threading.Thread(target=_watch_input, daemon=True).start()
    while True:
        t0   = time.monotonic()
        logo = render(angle)

        n   = max(len(logo), len(info))
        out=[]
        for i in range(n):
            lp = logo[i] if i < len(logo) else LOGO_W
            ip = info[i] if i < len(info) else ''
            out.append(f' {lp}{RST}  {ip}{RST}')
        out.append('')   # trailing newline, no extra RST line needed

        sys.stdout.write(HOME + RST + '\n'.join(out)+prompt)
        sys.stdout.flush()

        angle += step
        if angle >= 2.0 * math.pi:
            angle -= 2.0 * math.pi
            spins += 1
            if once:
                break

        # Linger on frontal view, zip through edge-on
        dt     = time.monotonic() - t0
        target = 1.0 / fps
        time.sleep(max(0.0, target - dt))

    bye()


if __name__ == '__main__':
    main()
