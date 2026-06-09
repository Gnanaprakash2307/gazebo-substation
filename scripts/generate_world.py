#!/usr/bin/env python3
"""Generate substation_phase2.sdf — clean orthogonal 3-phase wiring."""

from pathlib import Path
import math

# ── Phase constants (fixed order: A left, B center, C right) ──────────────────
PHASES = {
    'A': {'x': -3.0, 'z': 5.0, 'color': 'red',    'bb': 'busbar_a', 'ct': 'ct_transformer_a',
          'pt': 'pt_transformer_a', 'brk': 'breaker_single_a', 'xfmr_bush_x': -1.0},
    'B': {'x':  0.0, 'z': 5.4, 'color': 'yellow', 'bb': 'busbar_b', 'ct': 'ct_transformer_b',
          'pt': 'pt_transformer_b', 'brk': 'breaker_single_b', 'xfmr_bush_x':  0.0},
    'C': {'x':  3.0, 'z': 5.8, 'color': 'blue',   'bb': 'busbar_c', 'ct': 'ct_transformer_c',
          'pt': 'pt_transformer_c', 'brk': 'breaker_single_c', 'xfmr_bush_x':  1.0},
}

# ── Yard layout (Y+: north/incoming, Y-: south/outgoing) ─────────────────────
Y = {
    'tower':       14.0,
    'gantry_in':   10.0,
    'disconnector': 8.0,
    'ct':           6.5,
    'breaker_in':   5.0,
    'busbar':       0.0,
    'xfmr_feeder': -3.0,
    'breaker_out': -4.0,
    'ds_out':      -6.5,
    'gantry_out':  -9.0,
    'exit':       -12.0,
    'xfmr':        -6.0,
    'la':          -3.0,
    'ctrl':       -12.0,
}

X = {'busbar_w': -6.0, 'busbar_e': 6.0, 'pt': -7.0, 'tower': 0.0}

PI2 = math.pi / 2


def snap_length(length):
    """Snap to nearest 0.5 m so pre-built wire models fit."""
    return max(0.5, round(length * 2) / 2)


def ensure_wire_models(models_dir: Path):
    """Create wire segment models for every 0.5 m length up to 14 m."""
    colors = {
        'red': (0.85, 0.12, 0.12),
        'yellow': (0.90, 0.75, 0.10),
        'blue': (0.15, 0.35, 0.85),
    }
    for color, rgb in colors.items():
        for half in range(1, 29):  # 0.5 .. 14.0
            length = half * 0.5
            name = f'wire_{length:.1f}m_{color}'.replace('.', 'p')
            folder = models_dir / name
            if folder.exists():
                continue
            folder.mkdir(parents=True)
            r, g, b = rgb
            sdf = f'''<?xml version="1.0"?>
<sdf version="1.10"><model name="{name}"><static>true</static>
<link name="link"><visual name="wire">
<geometry><cylinder><radius>0.04</radius><length>{length}</length></cylinder></geometry>
<material><ambient>{r*0.8:.3f} {g*0.8:.3f} {b*0.8:.3f} 1</ambient>
<diffuse>{r:.3f} {g:.3f} {b:.3f} 1</diffuse></material></visual></link></model></sdf>'''
            cfg = (f'<?xml version="1.0"?><model><name>{name}</name>'
                   f'<version>1.0</version><sdf version="1.10">model.sdf</sdf></model>\n')
            (folder / 'model.sdf').write_text(sdf)
            (folder / 'model.config').write_text(cfg)


def wire(name, color, length, x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
    length = snap_length(length)
    tag = f'{length:.1f}m'.replace('.', 'p')
    return (
        f'  <include><uri>model://wire_{tag}_{color}</uri>'
        f'<name>{name}</name>'
        f'<pose>{x:.3f} {y:.3f} {z:.3f} {roll:.5f} {pitch:.5f} {yaw:.5f}</pose></include>'
    )


def along_y(name, color, length, x, yc, z):
    return wire(name, color, length, x, yc, z, PI2, 0, 0)


def along_x(name, color, length, xc, y, z):
    return wire(name, color, length, xc, y, z, 0, PI2, 0)


def along_z(name, color, length, x, y, zc):
    return wire(name, color, length, x, y, zc, 0, 0, 0)


def insulator(name, x, y, z):
    return (
        f'  <include><uri>model://insulator</uri>'
        f'<name>{name}</name>'
        f'<pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose></include>'
    )


def model_uri(model, name, x, y, z, yaw=0.0):
    return (
        f'  <include><uri>model://{model}</uri>'
        f'<name>{name}</name>'
        f'<pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.5f}</pose></include>'
    )


def equip_tap(prefix, color, x, y, z_high, z_low=0.85):
    """Vertical tap from conductor highway to equipment terminal."""
    length = snap_length(z_high - z_low)
    zc = z_high - length / 2
    return along_z(f'{prefix}_tap', color, length, x, y, zc)


def incoming_route(phase, p):
    """Tower → Gantry → DS → CT → Breaker → Busbar (orthogonal, constant Z)."""
    x, z, c = p['x'], p['z'], p['color']
    lines = []

    # Align from tower crossarm to phase column at y=tower
    if phase == 'A':
        lines.append(along_x(f'{phase}_tower_align', c, 1.5, -2.25, Y['tower'], z))
    elif phase == 'C':
        lines.append(along_x(f'{phase}_tower_align', c, 1.5, 2.25, Y['tower'], z))

    # Highway: tower → gantry → disconnector → CT → breaker → busbar
    spans = [
        ('tower_gantry',   (Y['tower'] + Y['gantry_in']) / 2,       Y['tower'] - Y['gantry_in']),
        ('gantry_ds',      (Y['gantry_in'] + Y['disconnector']) / 2, Y['gantry_in'] - Y['disconnector']),
        ('ds_ct',          (Y['disconnector'] + Y['ct']) / 2,       Y['disconnector'] - Y['ct']),
        ('ct_brk',         (Y['ct'] + Y['breaker_in']) / 2,         Y['ct'] - Y['breaker_in']),
        ('brk_bus',        (Y['breaker_in'] + Y['busbar']) / 2,     Y['breaker_in'] - Y['busbar']),
    ]
    for seg, yc, length in spans:
        lines.append(along_y(f'{phase}_{seg}', c, round(length, 1), x, yc, z))

    # Equipment taps (vertical only at equipment locations)
    for loc in ('disconnector', 'ct', 'breaker_in'):
        lines.append(equip_tap(f'{phase}_{loc}', c, x, Y[loc], z))

    # Insulators at gantry and busbar tie-in
    lines.append(insulator(f'ins_{phase}_gantry', x, Y['gantry_in'], z + 0.15))
    lines.append(insulator(f'ins_{phase}_busbar', x, Y['busbar'], z))

    return lines


def pt_tap(phase, p):
    """West branch: busbar → drop → lane route → PT (no crossing)."""
    x, z, c = p['x'], p['z'], p['color']
    pt_y = {'A': -0.5, 'B': 0.0, 'C': 0.5}[phase]
    lane_z = 1.2
    lines = [
        insulator(f'ins_{phase}_pt_bus', x, Y['busbar'], z),
        along_z(f'{phase}_pt_drop1', c, snap_length(z - lane_z), x, Y['busbar'], z - snap_length(z - lane_z) / 2),
    ]
    if abs(pt_y) > 0.01:
        lines.append(along_y(f'{phase}_pt_lane', c, abs(pt_y), x, pt_y / 2, lane_z))
    lines += [
        along_x(f'{phase}_pt_west', c, abs(x - X['pt']), (x + X['pt']) / 2, pt_y, lane_z),
        insulator(f'ins_{phase}_pt', X['pt'], pt_y, lane_z),
        along_z(f'{phase}_pt_drop2', c, snap_length(lane_z - 0.9), X['pt'], pt_y, lane_z - snap_length(lane_z - 0.9) / 2),
    ]
    return lines


def transformer_feeder(phase, p):
    """Busbar → 90° route → transformer bushing (no crossing)."""
    x, z, c = p['x'], p['z'], p['color']
    bx, by = p['xfmr_bush_x'], Y['xfmr']
    bush_z = 4.35
    lines = []

    # South on phase column to feeder plane
    lines.append(along_y(f'{phase}_xfmr_s1', c, abs(Y['busbar'] - Y['xfmr_feeder']),
                         x, (Y['busbar'] + Y['xfmr_feeder']) / 2, z))

    if phase in ('A', 'C'):
        # 90° turn toward bushing X, then south to transformer
        x_mid = (x + bx) / 2
        lines.append(along_x(f'{phase}_xfmr_x', c, abs(x - bx), x_mid, Y['xfmr_feeder'], z))
        lines.append(along_y(f'{phase}_xfmr_s2', c, abs(Y['xfmr_feeder'] - by),
                             bx, (Y['xfmr_feeder'] + by) / 2, z))
    else:
        lines.append(along_y(f'{phase}_xfmr_s2', c, abs(Y['xfmr_feeder'] - by),
                             bx, (Y['xfmr_feeder'] + by) / 2, z))

    lines.append(insulator(f'ins_{phase}_xfmr', bx, by, bush_z + 0.15))
    lines.append(along_z(f'{phase}_xfmr_drop', c, snap_length(z - bush_z), bx, by, z - snap_length(z - bush_z) / 2))
    return lines


def outgoing_route(phase, p):
    """Busbar → Breaker → DS → Gantry → exit (south bay)."""
    x, z, c = p['x'], p['z'], p['color']
    lines = []

    spans = [
        ('out_brk',  (Y['busbar'] + Y['breaker_out']) / 2,  abs(Y['busbar'] - Y['breaker_out'])),
        ('out_ds',   (Y['breaker_out'] + Y['ds_out']) / 2,  abs(Y['breaker_out'] - Y['ds_out'])),
        ('out_gantry', (Y['ds_out'] + Y['gantry_out']) / 2, abs(Y['ds_out'] - Y['gantry_out'])),
        ('out_exit', (Y['gantry_out'] + Y['exit']) / 2,     abs(Y['gantry_out'] - Y['exit'])),
    ]
    for seg, yc, length in spans:
        lines.append(along_y(f'{phase}_{seg}', c, round(length, 1), x, yc, z))

    for loc in ('breaker_out', 'ds_out'):
        lines.append(equip_tap(f'{phase}_{loc}', c, x, Y[loc], z))

    lines.append(insulator(f'ins_{phase}_out_gantry', x, Y['gantry_out'], z + 0.15))
    return lines


def main():
    pkg = Path(__file__).resolve().parents[1]
    ensure_wire_models(pkg / 'models')

    parts = [
        '<?xml version="1.0"?>',
        '<sdf version="1.10">',
        '<world name="substation">',
        '',
        '  <!-- Default overview camera (top-front isometric) -->',
        '  <gui fullscreen="0">',
        '    <camera name="user_camera">',
        '      <pose>18 -16 14 0 0.55 2.35</pose>',
        '    </camera>',
        '  </gui>',
        '',
        '  <!-- ========== ENVIRONMENT ========== -->',
        model_uri('ground', 'ground', 0, 0, 0),
        model_uri('yard_gravel_pad', 'yard_equipment_pad', 0, 1, 0),
        model_uri('oil_containment', 'oil_containment_zone', 0, Y['xfmr'], 0),
        model_uri('walkway', 'walkway_main', -9, 0, 0),
        model_uri('cable_trench', 'cable_trench_main', 0, 0, 0),
        '',
        '  <!-- ========== PERIMETER ========== -->',
        model_uri('fence', 'fence_north', 0, 18, 1.25),
        model_uri('fence', 'fence_south', 0, -18, 1.25),
        model_uri('fence', 'fence_east', 18, 0, 1.25, PI2),
        model_uri('fence', 'fence_west', -18, 0, 1.25, PI2),
        model_uri('name_board', 'substation_name_board', 0, 16.5, 0),
        model_uri('warning_sign', 'warning_sign_incoming', -8, 11, 0),
        model_uri('warning_sign', 'warning_sign_outgoing', -8, -10, 0),
        '',
        '  <!-- ========== INCOMING TRANSMISSION (NORTH) ========== -->',
        model_uri('tower', 'tower_incoming', X['tower'], Y['tower'], 0),
        model_uri('gantry', 'gantry_incoming', 0, Y['gantry_in'], 0),
        '',
        '  <!-- ========== INCOMING BAY (N→S: DS → CT → Breaker) ========== -->',
    ]

    for phase, p in PHASES.items():
        brk_name = {'A': 'breaker_left', 'B': 'breaker_center', 'C': 'breaker_right'}[phase]
        parts += [
            f'  <!-- Phase {phase} incoming -->',
            model_uri('disconnector', f'disconnector_in_{phase.lower()}', p['x'], Y['disconnector'], 0),
            model_uri(p['ct'], f'ct_{phase.lower()}', p['x'], Y['ct'], 0),
            model_uri(p['brk'], brk_name, p['x'], Y['breaker_in'], 0),
        ]

    parts += [
        '',
        '  <!-- ========== BUSBAR BRIDGE (yard center) ========== -->',
        model_uri('busbar_support', 'busbar_support_west', X['busbar_w'], Y['busbar'], 0),
        model_uri('busbar_support', 'busbar_support_east', X['busbar_e'], Y['busbar'], 0),
        insulator('ins_busbar_w_a', X['busbar_w'], Y['busbar'], 5.0),
        insulator('ins_busbar_w_b', X['busbar_w'], Y['busbar'], 5.4),
        insulator('ins_busbar_w_c', X['busbar_w'], Y['busbar'], 5.8),
        insulator('ins_busbar_e_a', X['busbar_e'], Y['busbar'], 5.0),
        insulator('ins_busbar_e_b', X['busbar_e'], Y['busbar'], 5.4),
        insulator('ins_busbar_e_c', X['busbar_e'], Y['busbar'], 5.8),
    ]
    for phase, p in PHASES.items():
        parts.append(model_uri(p['bb'], f'busbar_{phase.lower()}', 0, Y['busbar'], p['z']))

    parts += ['', '  <!-- ========== PT VOLTAGE SENSING (west branch) ========== -->']
    for phase, p in PHASES.items():
        pt_y = {'A': -0.5, 'B': 0.0, 'C': 0.5}[phase]
        parts.append(model_uri(p['pt'], f'pt_{phase.lower()}', X['pt'], pt_y, 0))

    parts += [
        '',
        '  <!-- ========== TRANSFORMER BAY (south center) ========== -->',
        model_uri('transformer_pad', 'transformer_pad_main', 0, Y['xfmr'], 0),
        model_uri('transformer', 'transformer_main', 0, Y['xfmr'], 0.5),
        model_uri('lightning_arrester', 'arrester_surge_protection', 0, Y['la'], 0),
        insulator('ins_arrester_top', 0, Y['la'], 8.0),
        '',
        '  <!-- ========== OUTGOING FEEDER BAY (SOUTH) ========== -->',
        model_uri('gantry', 'gantry_outgoing', 0, Y['gantry_out'], 0),
    ]
    for phase, p in PHASES.items():
        parts += [
            model_uri('disconnector', f'disconnector_out_{phase.lower()}', p['x'], Y['ds_out'], 0),
            model_uri(p['brk'], f'breaker_out_{phase.lower()}', p['x'], Y['breaker_out'], 0),
        ]

    parts += [
        model_uri('control_room', 'control_room_main', 0, Y['ctrl'], 0.8),
        '',
        '  <!-- ========== WIRING: INCOMING (rebuilt orthogonal) ========== -->',
    ]
    for phase, p in PHASES.items():
        parts.extend(incoming_route(phase, p))

    parts += ['', '  <!-- ========== WIRING: PT TAPS ========== -->']
    for phase, p in PHASES.items():
        parts.extend(pt_tap(phase, p))

    parts += ['', '  <!-- ========== WIRING: TRANSFORMER FEEDERS ========== -->']
    for phase, p in PHASES.items():
        parts.extend(transformer_feeder(phase, p))

    parts += ['', '  <!-- ========== WIRING: OUTGOING FEEDER ========== -->']
    for phase, p in PHASES.items():
        parts.extend(outgoing_route(phase, p))

    parts += [
        '',
        '  <!-- ========== LIGHTING ========== -->',
        '  <light name="sun" type="directional">',
        '    <pose>0 0 50 0 0 0</pose>',
        '    <cast_shadows>true</cast_shadows>',
        '    <diffuse>1 1 1 1</diffuse>',
        '    <specular>0.4 0.4 0.4 1</specular>',
        '    <direction>-0.5 -0.4 -1</direction>',
        '  </light>',
        '',
        '</world>',
        '</sdf>',
        '',
    ]

    out = pkg / 'worlds' / 'substation_phase2.sdf'
    out.write_text('\n'.join(parts))
    print(f'Wrote {out} ({len(parts)} lines)')


if __name__ == '__main__':
    main()
