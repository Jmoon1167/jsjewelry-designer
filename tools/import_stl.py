"""Convert a JS Jewelry metal-only ring STL into the designer's ring assets.

python convert.py STL SETTING_ID --cut round --girdle-y 16.25 --radius 5.5 \
    --offset-x 60 --designer /home/claude/jsjewelry-designer

Writes public/assets/rings/<id>-<cut>.glb and public/assets/fit/<id>-<cut>.fit.
Input STL: millimetres, Z up, finger-hole axis along Y (Matrix/Rhino default).
Designer frame: millimetres, Y up, finger-hole axis along Z.
"""

import argparse, gzip, json, struct
from pathlib import Path
import numpy as np
import trimesh


def read_glb(path):
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20 : 20 + n])
    return j, b[20 + n + 8 :]


def accessor(j, binary, i):
    a = j["accessors"][i]
    v = j["bufferViews"][a["bufferView"]]
    dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}[a["componentType"]]
    k = {"VEC3": 3, "SCALAR": 1}[a["type"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    arr = np.frombuffer(binary, dt, a["count"] * k, off)
    return arr.reshape(-1, k) if k > 1 else arr


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl")
    ap.add_argument("setting")
    ap.add_argument("--cut", default="round")
    ap.add_argument("--girdle-y", type=float, required=True)
    ap.add_argument("--radius", type=float, required=True)
    ap.add_argument("--offset-x", type=float, default=0)
    ap.add_argument("--head-base", type=float, required=True)
    ap.add_argument("--center-z", type=float, default=0.0)
    ap.add_argument("--designer", default="/home/claude/jsjewelry-designer")
    a = ap.parse_args()
    root = Path(a.designer) / "public" / "assets"

    mesh = trimesh.load(a.stl, process=True)
    mesh.merge_vertices()
    v = mesh.vertices.copy()
    v[:, 0] -= a.offset_x
    # Z-up / Y-axis  ->  Y-up / Z-axis (proper rotation about X).
    v = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)
    mesh = trimesh.Trimesh(v, mesh.faces, process=True)
    if mesh.volume < 0:
        mesh.invert()
    assert len(mesh.vertices) < 65535, "decimate first"
    pos = mesh.vertices.astype(np.float32)
    # Same convention as three.js computeVertexNormals (area-weighted), with a
    # fallback where opposing faces cancel so no vertex has a zero normal.
    tri = mesh.vertices[mesh.faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    acc = np.zeros_like(mesh.vertices)
    for k in range(3):
        np.add.at(acc, mesh.faces[:, k], cross)
    length = np.linalg.norm(acc, axis=1)
    weak = length < 1e-6
    if weak.any():
        unit = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
        fallback = np.zeros_like(acc)
        for k in range(3):
            fallback[mesh.faces[:, k]] = unit
        acc[weak] = fallback[weak]
        length = np.linalg.norm(acc, axis=1)
    nrm = (acc / length[:, None]).astype(np.float32)
    idx = mesh.faces.astype(np.uint16).ravel()

    # Reference center stone of the requested cut from a stock solitaire.
    ref, refbin = read_glb(root / "rings" / f"solitaire-{a.cut}.glb")
    cnode = next(n for n in ref["nodes"] if n.get("extras", {}).get("role") == "center")
    prim = ref["meshes"][cnode["mesh"]]["primitives"][0]
    spos = accessor(ref, refbin, prim["attributes"]["POSITION"]).astype(np.float32)
    snrm = accessor(ref, refbin, prim["attributes"]["NORMAL"]).astype(np.float32)
    sidx = accessor(ref, refbin, prim["indices"]).astype(np.uint16)
    ref_scale = cnode["scale"][0]
    ref_carats = cnode["extras"]["diamondCarats"]
    carats = ref_carats * (a.radius / ref_scale) ** 3

    # Carat field: the head scales about the girdle center, the shank stays.
    # Like the stock settings, the whole head scales about its base point.
    g = np.array([0, a.girdle_y, a.center_z], np.float32)
    base = np.array([0, a.head_base, a.center_z], np.float32)
    w = smoothstep(a.head_base - 2.5, a.head_base + 0.5, pos[:, 1])[:, None]
    d = w * (pos - base)
    field = np.clip(np.round(d * 1000), -32767, 32767).astype(np.int16)
    count = len(pos)
    blocks = [field.T.ravel()] + [np.zeros(count * 3, np.int16)] * 3
    fit = (
        struct.pack(">I", 0x46495431)
        + struct.pack("<II", count, 1)
        + (g - base).astype(np.float32).tobytes()
        + np.concatenate(blocks).tobytes()
    )
    assert len(fit) == 12 + 12 + count * 24

    # GLB
    chunks, views, accs = [], [], []

    def add(arr, target, kind, comp, mm=False):
        off = sum(len(c) for c in chunks)
        data = arr.tobytes()
        data += b"\0" * (-len(data) % 4)
        chunks.append(data)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(arr.tobytes()), "target": target})
        acc = {"bufferView": len(views) - 1, "componentType": comp,
               "count": len(arr) if arr.ndim > 1 else arr.size, "type": kind}
        if mm:
            acc["min"] = arr.min(0).tolist(); acc["max"] = arr.max(0).tolist()
        accs.append(acc)
        return len(accs) - 1

    bp = add(pos, 34962, "VEC3", 5126, True)
    bn = add(nrm, 34962, "VEC3", 5126)
    bi = add(idx, 34963, "SCALAR", 5123)
    sp = add(spos, 34962, "VEC3", 5126, True)
    sn = add(snrm, 34962, "VEC3", 5126)
    si = add(sidx, 34963, "SCALAR", 5123)
    extras = dict(cnode["extras"])
    extras.update(mmPerUnit=a.radius, diamondCarats=carats, cut=a.cut)
    allpts = np.vstack([pos, spos * a.radius + g])
    inner = np.hypot(pos[:, 0], pos[:, 1])
    band_d = 2 * float(inner[(np.abs(pos[:, 2]) < 1) & (pos[:, 1] < 0)].min())
    gl = {
        "asset": {"version": "2.0", "generator": "JS Jewelry STL import"},
        "scene": 0,
        "scenes": [{"nodes": [0, 1], "extras": {
            "bounds": [allpts.min(0).tolist(), allpts.max(0).tolist()],
            "bandDiameter": band_d, "carats": carats}}],
        "nodes": [
            {"name": "band", "mesh": 0, "extras": {"role": "band"}},
            {"name": "center", "mesh": 1, "extras": extras,
             "translation": g.tolist(), "rotation": [0, 0, 0, 1], "scale": [a.radius] * 3},
        ],
        "meshes": [
            {"name": "band", "primitives": [{"attributes": {"POSITION": bp, "NORMAL": bn}, "indices": bi, "material": 0}]},
            {"name": "center", "primitives": [{"attributes": {"POSITION": sp, "NORMAL": sn}, "indices": si, "material": 1}]},
        ],
        "materials": ref["materials"],
        "bufferViews": views,
        "accessors": accs,
        "buffers": [{"byteLength": sum(len(c) for c in chunks)}],
    }
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binary = b"".join(chunks)
    out = (b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(binary))
           + struct.pack("<I", len(js)) + b"JSON" + js
           + struct.pack("<I", len(binary)) + b"BIN\0" + binary)
    rid = f"{a.setting}-{a.cut}"
    (root / "rings" / f"{rid}.glb").write_bytes(out)
    (root / "fit" / f"{rid}.fit").write_bytes(gzip.compress(fit, 9))
    print(rid, "verts", count, "carats", round(carats, 2), "band", round(band_d, 2))


main()
