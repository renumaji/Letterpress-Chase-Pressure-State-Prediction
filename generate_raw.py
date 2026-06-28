from __future__ import annotations

import hashlib
import random
from pathlib import Path

import pandas as pd


SEED = 842771
N_CASES = 4200
ZONES = [f"Z{i}" for i in range(8)]
STOCKS = ["rag", "cotton", "newsprint", "vellum"]
HUMIDITY = ["dry", "steady", "damp"]
ORIENTATIONS = ["north", "east", "south", "west"]
OPS = ["SHIFT", "SPLIT", "TIGHTEN", "RELIEF", "SWELL", "SMEAR", "CLAMP", "ROTATE"]


def stable_id(text: str) -> str:
    return "lp_" + hashlib.sha256(text.encode()).hexdigest()[:15]


def empty_zone() -> dict[str, float]:
    return {"force": 0.0, "ink": 0.0, "lift": 0.0, "slip": 0.0}


def add(zone: dict[str, float], force: float, ink: float, lift: float, slip: float) -> None:
    force = max(float(force), 0.0)
    if force <= 0:
        return
    old = zone["force"]
    new = old + force
    zone["ink"] = (zone["ink"] * old + ink * force) / new
    zone["lift"] = (zone["lift"] * old + lift * force) / new
    zone["slip"] = (zone["slip"] * old + slip * force) / new
    zone["force"] = new


def take(zone: dict[str, float], force: float) -> dict[str, float]:
    got = min(max(float(force), 0.0), zone["force"])
    out = {"force": got, "ink": zone["ink"], "lift": zone["lift"], "slip": zone["slip"]}
    zone["force"] -= got
    if zone["force"] <= 1e-9:
        zone.update(empty_zone())
    return out


def material(kind: str) -> tuple[float, float, float]:
    if kind == "METAL":
        return 0.92, 0.18, 0.16
    if kind == "WOOD":
        return 0.48, 0.46, 0.22
    if kind == "SPACER":
        return 0.12, 0.72, 0.18
    if kind == "QUOIN":
        return 0.24, 0.16, 0.58
    raise ValueError(kind)


def execute(state: dict[str, dict[str, float]], op: str) -> None:
    p = op.split()
    cmd = p[0]
    if cmd == "PLACE":
        _, zone, kind, force = p
        add(state[zone], float(force), *material(kind))
    elif cmd == "SHIFT":
        _, src, dst, force, loss = p
        payload = take(state[src], float(force))
        add(state[dst], payload["force"] * (1.0 - float(loss)), payload["ink"], payload["lift"], payload["slip"])
    elif cmd == "SPLIT":
        _, src, dst_a, dst_b, force, frac, loss = p
        payload = take(state[src], float(force))
        delivered = payload["force"] * (1.0 - float(loss))
        frac = float(frac)
        add(state[dst_a], delivered * frac, payload["ink"], payload["lift"], payload["slip"])
        add(state[dst_b], delivered * (1.0 - frac), payload["ink"], payload["lift"], payload["slip"])
    elif cmd == "TIGHTEN":
        _, zone, gain, slip_gain = p
        state[zone]["force"] *= 1.0 + float(gain)
        state[zone]["slip"] = min(1.0, state[zone]["slip"] + float(slip_gain))
    elif cmd == "RELIEF":
        _, zone, force_loss, lift_gain = p
        state[zone]["force"] *= max(0.0, 1.0 - float(force_loss))
        state[zone]["lift"] = min(1.0, state[zone]["lift"] + float(lift_gain))
    elif cmd == "SWELL":
        _, zone, lift_gain, ink_loss = p
        state[zone]["lift"] = min(1.0, state[zone]["lift"] + float(lift_gain))
        state[zone]["ink"] *= max(0.0, 1.0 - float(ink_loss))
    elif cmd == "SMEAR":
        _, zone, ink_gain, slip_gain = p
        state[zone]["ink"] = min(1.0, state[zone]["ink"] + float(ink_gain))
        state[zone]["slip"] = min(1.0, state[zone]["slip"] + float(slip_gain))
    elif cmd == "CLAMP":
        _, zone, max_force = p
        state[zone]["force"] = min(state[zone]["force"], float(max_force))
    elif cmd == "ROTATE":
        _, steps = p
        steps = int(steps) % len(ZONES)
        old = {z: dict(state[z]) for z in ZONES}
        for i, z in enumerate(ZONES):
            state[ZONES[(i + steps) % len(ZONES)]] = old[z]


def feature_counts(program: list[str], target_zone: str) -> dict[str, int]:
    counts = {f"count_{op.lower()}": 0 for op in OPS}
    for op in program:
        cmd = op.split()[0]
        key = f"count_{cmd.lower()}"
        if key in counts:
            counts[key] += 1
    idx = ZONES.index(target_zone)
    return {
        **counts,
        "target_zone_idx": idx,
        "corner_zone": int(idx in {0, 7}),
        "split_heavy": int(counts["count_split"] >= 3),
        "rotate_heavy": int(counts["count_rotate"] >= 3),
        "smear_heavy": int(counts["count_smear"] >= 3),
        "relief_heavy": int(counts["count_relief"] >= 3),
    }


def build_case(rng: random.Random, idx: int) -> dict[str, object]:
    paper_stock = rng.choice(STOCKS)
    humidity_band = rng.choice(HUMIDITY)
    forme_orientation = rng.choice(ORIENTATIONS)
    state = {zone: empty_zone() for zone in ZONES}
    program: list[str] = []

    for zone in rng.sample(ZONES, rng.choice([3, 4, 5])):
        op = f"PLACE {zone} {rng.choice(['METAL', 'WOOD', 'SPACER', 'QUOIN'])} {rng.choice([8, 12, 17, 23, 31])}"
        program.append(op)
        execute(state, op)

    for _ in range(rng.randint(28, 48)):
        occupied = [zone for zone in ZONES if state[zone]["force"] > 0.4]
        cmd = rng.choices(OPS, weights=[6, 4, 4, 4, 3, 3, 2, 3])[0]
        if cmd == "SHIFT" and occupied:
            op = f"SHIFT {rng.choice(occupied)} {rng.choice(ZONES)} {rng.choice([3, 5, 8, 13, 19])} {rng.choice([0.00, 0.03, 0.07, 0.12]):.2f}"
        elif cmd == "SPLIT" and occupied:
            a, b = rng.sample(ZONES, 2)
            op = f"SPLIT {rng.choice(occupied)} {a} {b} {rng.choice([5, 9, 15, 22])} {rng.choice([0.20, 0.35, 0.50, 0.65, 0.80]):.2f} {rng.choice([0.00, 0.04, 0.09]):.2f}"
        elif cmd == "TIGHTEN":
            op = f"TIGHTEN {rng.choice(ZONES)} {rng.choice([0.04, 0.10, 0.18, 0.31]):.2f} {rng.choice([0.00, 0.03, 0.08, 0.14]):.2f}"
        elif cmd == "RELIEF":
            op = f"RELIEF {rng.choice(ZONES)} {rng.choice([0.04, 0.09, 0.16, 0.28]):.2f} {rng.choice([0.00, 0.05, 0.11, 0.20]):.2f}"
        elif cmd == "SWELL":
            op = f"SWELL {rng.choice(ZONES)} {rng.choice([0.02, 0.06, 0.13, 0.22]):.2f} {rng.choice([0.00, 0.04, 0.10, 0.18]):.2f}"
        elif cmd == "SMEAR":
            op = f"SMEAR {rng.choice(ZONES)} {rng.choice([0.03, 0.07, 0.14, 0.24]):.2f} {rng.choice([0.00, 0.04, 0.09, 0.16]):.2f}"
        elif cmd == "CLAMP":
            op = f"CLAMP {rng.choice(ZONES)} {rng.choice([18, 28, 42, 60])}"
        else:
            op = f"ROTATE {rng.choice([1, 2, 3, 5, 7])}"
        program.append(op)
        execute(state, op)

    target_zone = rng.choice(ZONES)
    final = state[target_zone]
    force = max(0.0, final["force"])
    ink = 100.0 * final["ink"]
    lift = 100.0 * final["lift"]
    slip = 100.0 * final["slip"]
    feat = feature_counts(program, target_zone)

    stock_scale = {"rag": 1.06, "cotton": 0.92, "newsprint": 1.21, "vellum": 0.81}[paper_stock]
    humidity_scale = {"dry": 1.14, "steady": 1.00, "damp": 0.78}[humidity_band]
    orientation_offset = {"north": -1.5, "east": 2.2, "south": 0.7, "west": -0.4}[forme_orientation]
    force = force * stock_scale * humidity_scale + orientation_offset
    if feat["split_heavy"]:
        force *= 0.82
    if feat["rotate_heavy"] and forme_orientation in {"east", "west"}:
        force += 3.8
    if feat["corner_zone"] and humidity_band == "dry":
        force *= 1.18
    force = max(0.0, force)

    stock_comp = {
        "rag": (0.94, 1.15, 0.92),
        "cotton": (1.06, 0.96, 1.04),
        "newsprint": (1.22, 0.88, 1.16),
        "vellum": (0.84, 1.28, 0.80),
    }[paper_stock]
    humidity_comp = {
        "dry": (0.90, 0.84, 1.22),
        "steady": (1.00, 1.00, 1.00),
        "damp": (1.18, 1.24, 0.88),
    }[humidity_band]
    ink *= stock_comp[0] * humidity_comp[0]
    lift *= stock_comp[1] * humidity_comp[1]
    slip *= stock_comp[2] * humidity_comp[2]
    if feat["smear_heavy"]:
        ink *= 1.22
        slip *= 1.17
    if feat["relief_heavy"]:
        lift *= 1.25
        force *= 0.92
    if feat["target_zone_idx"] in {2, 3, 4}:
        ink *= 1.08
    if feat["target_zone_idx"] >= 6:
        slip *= 1.14
    total = max(ink + lift + slip, 1e-9)

    row = {
        "case_id": stable_id(f"{idx}|{'|'.join(program)}|{target_zone}"),
        "target_zone": target_zone,
        "lockup_trace": "; ".join(program),
        "operation_count": len(program),
        "paper_stock": paper_stock,
        "humidity_band": humidity_band,
        "forme_orientation": forme_orientation,
        "impression_force": round(force, 6),
        "ink_spread_pct": round(100.0 * ink / total, 6),
        "paper_lift_pct": round(100.0 * lift / total, 6),
        "slip_risk_pct": round(100.0 * slip / total, 6),
    }
    row.update({k: v for k, v in feat.items() if k.startswith("count_")})
    row["operation_bin_private"] = "short" if len(program) < 35 else "medium" if len(program) < 45 else "long"
    row["force_bin_private"] = "empty" if force < 1 else "low" if force < 14 else "mid" if force < 38 else "high"
    row["structure_private"] = (
        "rotate" if feat["rotate_heavy"] else "smear" if feat["smear_heavy"] else "relief" if feat["relief_heavy"] else "split" if feat["split_heavy"] else "ordinary"
    )
    return row


def main() -> None:
    rng = random.Random(SEED)
    df = pd.DataFrame([build_case(rng, i) for i in range(N_CASES)])
    Path("raw").mkdir(exist_ok=True)
    df.to_csv("raw/data.csv", index=False)
    df.to_csv("data.csv", index=False)
    print(f"Wrote {len(df)} rows")


if __name__ == "__main__":
    main()
