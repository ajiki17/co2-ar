"""ARモデル（.glb）を作る（v3）。使い方： python make_models_v3.py [data.json] [出力フォルダ]
  立方体：cube_day.glb（1日分）・cube_year.glb（1年分）・cube_life_10〜99.glb（年齢ごとの人生分）
  浸水　：flood_050.glb・flood_100.glb・flood_300.glb（0.5m・1.0m・3.0m）
数値はすべて data.json（数値台帳から書き出したもの）から計算する。単位はメートルで、実寸のまま。
必要なのは numpy と Pillow だけ（glb は自前で書き出す）。アニメーションは入れない（iPhone の AR Quick Look は非対応）。
作り直したら、index.html のモデルの版番号（?v=）を上げること。"""
import json, struct, sys, io, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "data.json", encoding="utf-8"))
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
RHO = D["densityKgPerM3"]
FONT = next((p for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
                         "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", "C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/meiryob.ttc"] if os.path.exists(p)), None)
font = lambda px: ImageFont.truetype(FONT, px) if FONT else ImageFont.load_default()

# ---------------------------------------------------------------- 形（頂点・法線・UV・面）
class Geo:
    def __init__(s): s.p, s.n, s.t, s.i = [], [], [], []
    def add(s, p, n, t, i):
        b = sum(len(x) for x in s.p); s.p.append(np.asarray(p, np.float32)); s.n.append(np.asarray(n, np.float32))
        s.t.append(np.asarray(t, np.float32) if t is not None else np.zeros((len(p), 2), np.float32)); s.i.append(np.asarray(i, np.uint32) + b); return s
    def quad(s, a, b, c, d, uv=((0, 1), (1, 1), (1, 0), (0, 0))):          # 左下・右下・右上・左上（UVは画像の左上が原点）
        a, b, c, d = (np.asarray(x, np.float32) for x in (a, b, c, d)); n = np.cross(b - a, d - a); n = n / (np.linalg.norm(n) or 1)
        return s.add([a, b, c, d], [n] * 4, uv, [0, 1, 2, 0, 2, 3])
    def box(s, w, h, d, x=0, y0=0, z=0, uvside=False):
        X, Y, Z = w / 2, h, d / 2; c = np.array([x, y0, z], np.float32)
        P = lambda *v: c + np.array(v, np.float32)
        f = [(P(-X, 0, Z), P(X, 0, Z), P(X, Y, Z), P(-X, Y, Z)), (P(X, 0, -Z), P(-X, 0, -Z), P(-X, Y, -Z), P(X, Y, -Z)),
             (P(X, 0, Z), P(X, 0, -Z), P(X, Y, -Z), P(X, Y, Z)), (P(-X, 0, -Z), P(-X, 0, Z), P(-X, Y, Z), P(-X, Y, -Z))]
        for q in f: s.quad(*q)                                              # 側面は v=1 が下、v=0 が上（縦のグラデーション用）
        s.quad(P(-X, Y, Z), P(X, Y, Z), P(X, Y, -Z), P(-X, Y, -Z), uv=((0, 0),) * 4); s.quad(P(-X, 0, -Z), P(X, 0, -Z), P(X, 0, Z), P(-X, 0, Z), uv=((0, 1),) * 4); return s
    def tube(s, r0, r1, h, x=0, y0=0, z=0, seg=12, sx=1.0, sz=1.0, tilt=0.0):  # 下の半径r0・上の半径r1。sx・szで楕円に。tiltはZ軸まわりの傾き（ラジアン）
        ang = np.linspace(0, 2 * np.pi, seg + 1); P, N = [], []
        for yy, r in ((0, r0), (h, r1)):
            for a in ang: P.append([math.cos(a) * r * sx, yy, math.sin(a) * r * sz]); N.append([math.cos(a) / sx, (r0 - r1) / max(h, 1e-6), math.sin(a) / sz])
        P, N = np.array(P, np.float32), np.array(N, np.float32); N /= np.linalg.norm(N, axis=1, keepdims=True)
        I = []
        for k in range(seg): a, b, c, d = k, k + 1, seg + 1 + k + 1, seg + 1 + k; I += [a, c, b, a, d, c]
        nc = len(P); P = np.vstack([P, [[0, h, 0]], [[0, 0, 0]]]); N = np.vstack([N, [[0, 1, 0]], [[0, -1, 0]]])
        for k in range(seg): I += [nc, seg + 1 + k + 1, seg + 1 + k, nc + 1, k, k + 1]
        if tilt: R = np.array([[math.cos(tilt), -math.sin(tilt), 0], [math.sin(tilt), math.cos(tilt), 0], [0, 0, 1]], np.float32); P, N = P @ R.T, N @ R.T
        return s.add(P + np.array([x, y0, z], np.float32), N, None, I)
    def ball(s, rx, ry, rz, x=0, y=0, z=0, seg=14, rings=9):
        P, I = [], []
        for j in range(rings + 1):
            v = math.pi * j / rings
            for k in range(seg + 1): u = 2 * math.pi * k / seg; P.append([math.sin(v) * math.cos(u), math.cos(v), math.sin(v) * math.sin(u)])
        for j in range(rings):
            for k in range(seg): a = j * (seg + 1) + k; b = a + seg + 1; I += [a, a + 1, b, a + 1, b + 1, b]
        P = np.array(P, np.float32); N = P / np.array([rx, ry, rz], np.float32); N /= np.linalg.norm(N, axis=1, keepdims=True)
        return s.add(P * np.array([rx, ry, rz], np.float32) + np.array([x, y, z], np.float32), N, None, I)
    def ring(s, r, w, x=0, y=0.006, z=0, seg=64):                            # 床に置く平らな輪（半径r・幅w）
        ang = np.linspace(0, 2 * np.pi, seg + 1); P, I = [], []
        for a in ang: P += [[x + math.cos(a) * (r - w / 2), y, z + math.sin(a) * (r - w / 2)], [x + math.cos(a) * (r + w / 2), y, z + math.sin(a) * (r + w / 2)]]
        for k in range(seg): a = 2 * k; I += [a, a + 1, a + 3, a, a + 3, a + 2, a, a + 3, a + 1, a, a + 2, a + 3]
        return s.add(P, [[0, 1, 0]] * len(P), None, I)
    def arrays(s): return np.vstack(s.p), np.vstack(s.n), np.vstack(s.t), np.concatenate(s.i)

def person(g, x, z, h=1.70):
    """身長h（既定1.70m）の、様式化した人のシルエット（頭・首・胴・腕・脚）"""
    k = h / 1.70
    for sx in (-1, 1):
        g.tube(.075 * k, .09 * k, .84 * k, x + sx * .095 * k, 0, z, sx=1, sz=1.05)                    # 脚
        g.tube(.04 * k, .052 * k, .64 * k, x + sx * .30 * k, .80 * k, z, tilt=sx * .13)                 # 腕
        g.ball(.06 * k, .045 * k, .11 * k, x + sx * .095 * k, .045 * k, z + .04 * k, seg=10, rings=5)    # 足先
    g.tube(.17 * k, .20 * k, .62 * k, x, .82 * k, z, seg=16, sx=1, sz=.62)                               # 胴（肩に向かって広がる）
    g.ball(.20 * k, .06 * k, .124 * k, x, 1.44 * k, z, seg=16, rings=6)                                  # 肩
    g.tube(.05 * k, .045 * k, .07 * k, x, 1.44 * k, z)                                                   # 首
    g.ball(.098 * k, .118 * k, .105 * k, x, 1.582 * k, z)                                                # 頭（頭頂＝h）
    return g

# ---------------------------------------------------------------- 画像（ラベル・目盛り・質感）
INK, SUB, ORANGE = (26, 29, 35), (76, 84, 98), (232, 112, 42)
def draw_text(d, xy, s, f, fill):
    """「CO₂」「m³」の小さな字は、フォントに無くても読めるように自分で小さく描く"""
    x, y = xy; small = font(int(f.size * .58)); sw = 2 if f.size >= 80 else 1          # 細い書体でも読みやすいように、少し太らせる
    for ch in s:
        if ch in "₂³":
            c = "2" if ch == "₂" else "3"; d.text((x, y + (f.size * .46 if ch == "₂" else -f.size * .04)), c, font=small, fill=fill, stroke_width=sw, stroke_fill=fill); x += d.textlength(c, font=small) + 1 + sw
        else: d.text((x, y), ch, font=f, fill=fill, stroke_width=sw, stroke_fill=fill); x += d.textlength(ch, font=f) + sw
    return x
def plate(big, small, w=1024, h=256, on=True):
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 18, h], fill=ORANGE if on else (150, 158, 172)); draw_text(d, (48, 34), big, font(92), INK); draw_text(d, (50, 152), small, font(54), SUB); return im
def tag(txt, w=256, h=112):
    im = Image.new("RGBA", (w, h), (11, 16, 32, 235)); d = ImageDraw.Draw(im); f = font(70); d.text(((w - d.textlength(txt, font=f)) / 2, 16), txt, font=f, fill=(255, 255, 255)); return im
def gradient(top, bottom, h=64):
    im = Image.new("RGBA", (4, h)); px = im.load()
    for y in range(h):
        t = y / (h - 1)
        for x in range(4): px[x, y] = tuple(int(round(top[k] * (1 - t) + bottom[k] * t)) for k in range(4))
    return im
def ripple(n=128):
    y, x = np.mgrid[0:n, 0:n] / n * 2 * np.pi
    v = .5 + .22 * np.sin(x * 3 + y * 2) + .16 * np.sin(x * 5 - y * 4 + 1.3) + .1 * np.sin(x * 9 + y * 7 + .5)
    a = np.zeros((n, n, 4), np.uint8); a[..., 0] = 40 + 70 * v; a[..., 1] = 150 + 70 * v; a[..., 2] = 165 + 70 * v; a[..., 3] = 255; return Image.fromarray(a)
def ruler(top=3.2, w=192, ppm=300):
    """0〜3mの目盛り板（0.1mごとの線、0.5mごとの数字）"""
    h = int(top * ppm); im = Image.new("RGBA", (w, h), (250, 250, 248, 255)); d = ImageDraw.Draw(im); f = font(50)
    for k in range(0, int(top * 10) + 1):
        y = h - 1 - int(k / 10 * ppm); major = k % 5 == 0
        d.rectangle([0, y - (3 if major else 1), w * (.5 if major else .26), y + (3 if major else 1)], fill=INK)
        if major and k: d.text((w * .5 + 8, y - 30), f"{k / 10:.1f}", font=f, fill=INK)
    for k in range(0, int(top * 2)):                                          # 0.5mごとに色分け（色だけでなく数字でも読める）
        if k % 2 == 0: d.rectangle([0, h - int((k + 1) * .5 * ppm), 14, h - int(k * .5 * ppm)], fill=ORANGE)
    return im
def png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()

# ---------------------------------------------------------------- glb の書き出し
def write_glb(path, parts):
    """parts：[(Geo, 材質の辞書)]。材質：color=[r,g,b,a]、image=PIL画像（任意）、blend=半透明、rough、double"""
    buf = bytearray(); views, accs, meshes, nodes, mats, imgs, texs = [], [], [], [], [], [], []
    def view(data, target=None):
        while len(buf) % 4: buf.append(0)
        v = {"buffer": 0, "byteOffset": len(buf), "byteLength": len(data)}
        if target: v["target"] = target
        buf.extend(data); views.append(v); return len(views) - 1
    for g, m in parts:
        P, N, T, I = g.arrays(); idx = I.astype(np.uint16 if len(P) < 65536 else np.uint32)
        a0 = len(accs)
        accs.append({"bufferView": view(P.tobytes(), 34962), "componentType": 5126, "count": len(P), "type": "VEC3", "min": P.min(0).tolist(), "max": P.max(0).tolist()})
        accs.append({"bufferView": view(N.tobytes(), 34962), "componentType": 5126, "count": len(N), "type": "VEC3"})
        accs.append({"bufferView": view(T.tobytes(), 34962), "componentType": 5126, "count": len(T), "type": "VEC2"})
        accs.append({"bufferView": view(idx.tobytes(), 34963), "componentType": 5123 if idx.dtype == np.uint16 else 5125, "count": len(idx), "type": "SCALAR"})
        mat = {"name": m.get("name", "m"), "pbrMetallicRoughness": {"baseColorFactor": m.get("color", [1, 1, 1, 1]), "metallicFactor": 0.0, "roughnessFactor": m.get("rough", 0.9)},
               "doubleSided": bool(m.get("double", False)), "alphaMode": "BLEND" if m.get("blend") else "OPAQUE"}
        if m.get("image") is not None:
            imgs.append({"bufferView": view(png(m["image"])), "mimeType": "image/png"}); texs.append({"source": len(imgs) - 1, "sampler": 0}); mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(texs) - 1}
        mats.append(mat); meshes.append({"name": m.get("name", "m"), "primitives": [{"attributes": {"POSITION": a0, "NORMAL": a0 + 1, "TEXCOORD_0": a0 + 2}, "indices": a0 + 3, "material": len(mats) - 1}]})
        nodes.append({"name": m.get("name", "m"), "mesh": len(meshes) - 1})
    while len(buf) % 4: buf.append(0)
    j = {"asset": {"version": "2.0", "generator": "co2-ar make_models_v3.py"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes, "materials": mats,
         "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    if imgs: j.update(images=imgs, textures=texs, samplers=[{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])
    js = json.dumps(j, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(buf))); f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js); f.write(struct.pack("<II", len(buf), 0x004E4942)); f.write(buf)
    return os.path.getsize(path)

BODY = dict(name="person", color=[.30, .33, .38, 1], rough=.85)
WHITE = dict(name="white", color=[.93, .96, 1, 1], rough=.6)
def stand(g_post, g_face, img_w, img_h, cx, cz, width, yc):
    """ラベル板：支柱つき。表と裏の両方から読める"""
    hh = width * img_h / img_w / 2
    g_face.quad([cx - width / 2, yc - hh, cz], [cx + width / 2, yc - hh, cz], [cx + width / 2, yc + hh, cz], [cx - width / 2, yc + hh, cz])
    g_face.quad([cx + width / 2, yc - hh, cz - .012], [cx - width / 2, yc - hh, cz - .012], [cx - width / 2, yc + hh, cz - .012], [cx + width / 2, yc + hh, cz - .012])
    g_post.box(max(.03, width * .02), yc - hh, max(.03, width * .02), cx, 0, cz - .006)

# ---------------------------------------------------------------- 立方体（体験1）
def fmt_side(s): return f"{s:.2f}" if s < 10 else f"{s:.1f}" if s < 30 else f"{s:.0f}"
def cube_model(path, kg, big, with_room=False):
    v = kg / RHO; s = v ** (1 / 3); small = f"体積 約{v:,.1f}m³（一辺{fmt_side(s)}m）" if v < 100 else f"体積 約{v:,.0f}m³（一辺{fmt_side(s)}m）"
    body, edge, dots, rings, post, face, tags, man = (Geo() for _ in range(8))
    body.box(s, s, s)                                                        # 面：下が濃く上が薄いグラデーション
    t = max(.014, s * .006)
    for sx in (-1, 1):
        for sz in (-1, 1): edge.box(t, s, t, sx * s / 2, 0, sz * s / 2)
        for y in (0, s - t): edge.box(t, t, s, sx * s / 2, y, 0); edge.box(s, t, t, 0, y, sx * s / 2)
    rng = np.random.default_rng(int(kg)); r = max(.012, s * .008)             # 中に漂う粒（位置は kg から決まるので、毎回同じ）
    for x, y, z in rng.uniform(-.47, .47, (140, 3)): dots.ball(r, r, r, x * s, (y + .5) * s, z * s, seg=4, rings=2)   # 粒は八面体（軽くするため）
    # 人（身長1.70m）と、足もとの1m刻みの輪。小さい立方体は立方体の中心、大きい立方体は人の足もとを中心にする
    px, pz = s / 2 + .55, s / 2 - .35; person(man, px, pz)
    cx, cz = (0, 0) if s < 4 else (px, pz)
    for k in (1, 2, 3):
        rings.ring(k, .03, cx, .006, cz); a = math.radians(38); tx, tz = cx + math.cos(a) * k, cz + math.sin(a) * k
        tags.quad([tx - .13, .02, tz], [tx + .13, .02, tz], [tx + .13, .134, tz], [tx - .13, .134, tz], uv=((0, (k) / 3), (1, (k) / 3), (1, (k - 1) / 3), (0, (k - 1) / 3)))
    w = min(max(1.5, s * .34), 12); stand(post, face, 1024, 256, min(0, px - w / 2 - .35) if s >= 4 else 0, s / 2 + .32 + (w * .02), w, max(1.15, w * .22))
    tagimg = Image.new("RGBA", (256, 336)); [tagimg.paste(tag(f"{k}m"), (0, (k - 1) * 112)) for k in (1, 2, 3)]
    parts = [(edge, dict(name="edge", color=[.78, .88, 1, 1], rough=.5)), (dots, dict(name="dots", color=[.86, .93, 1, 1], rough=.4)), (man, BODY), (rings, WHITE), (post, BODY),
             (face, dict(name="label", image=plate(big, small), rough=.8)), (tags, dict(name="tags", image=tagimg, rough=.8, double=True))]
    if with_room:                                                            # 比較用の6畳間（3.6m×2.7m×高さ2.4m）の枠
        room, rface = Geo(), Geo(); W, Hh, Dd = 3.6, 2.4, 2.7; rx = -(s / 2 + .5 + W / 2); rt = .02
        for sx in (-1, 1):
            for sz in (-1, 1): room.box(rt, Hh, rt, rx + sx * W / 2, 0, sz * Dd / 2)
            for y in (0, Hh - rt): room.box(rt, rt, Dd, rx + sx * W / 2, y, 0); room.box(W, rt, rt, rx, y, sx * Dd / 2)
        stand(room, rface, 1024, 256, rx, Dd / 2 + .3, 1.5, 1.15)
        parts += [(room, dict(name="room", color=[.85, .9, .97, 1], rough=.6)), (rface, dict(name="roomlabel", image=plate("6畳間", "3.6m×2.7m×高さ2.4m"), rough=.8))]
    parts.append((body, dict(name="co2", color=[1, 1, 1, .5], image=gradient((150, 200, 255, 120), (36, 104, 214, 205)), blend=True, double=True, rough=.35)))   # 半透明は最後に描く
    return write_glb(path, parts), s

# ---------------------------------------------------------------- 浸水（体験4）
FLOOD = {0.5: ("0.5m　床上浸水", "大人のひざの高さ"), 1.0: ("1.0m", "大人の腰の高さ"), 3.0: ("3.0m　2階の床まで", "1階は天井近くまで水につかる")}
def flood_model(path, h, half=4.0):
    surf, side, band, post, board, man = (Geo() for _ in range(6)); n = 44
    xs = np.linspace(-half, half, n + 1); X, Z = np.meshgrid(xs, xs); Y = h + .012 * np.sin(X * 2.1 + Z * 1.3) + .009 * np.sin(X * 3.7 - Z * 2.9 + 1.1) + .006 * np.sin(Z * 5.3 + .4)   # 水面の凹凸
    edge = np.minimum(np.minimum(X + half, half - X), np.minimum(Z + half, half - Z)); Y = h + (Y - h) * np.clip(edge / .4, 0, 1)                                              # ふちは水位ちょうどに
    P = np.stack([X, Y, Z], -1).reshape(-1, 3); gy, gx = np.gradient(Y, xs, xs); N = np.stack([-gx, np.ones_like(Y), -gy], -1).reshape(-1, 3); N /= np.linalg.norm(N, axis=1, keepdims=True)
    T = np.stack([(X + half) / 1.6, (Z + half) / 1.6], -1).reshape(-1, 2); I = []
    for a in range(n):
        for b in range(n): k = a * (n + 1) + b; I += [k, k + n + 1, k + 1, k + 1, k + n + 1, k + n + 2]
    surf.add(P, N, T, I)
    c = [(-half, half), (half, half), (half, -half), (-half, -half)]
    for k in range(4): (x0, z0), (x1, z1) = c[k], c[(k + 1) % 4]; side.quad([x0, 0, z0], [x1, 0, z1], [x1, h, z1], [x0, h, z0])                                             # 側面：深いほど濃い
    bw, bh = .05, .035
    for sgn in (-1, 1): band.box(2 * half + bw, bh, bw, 0, h - bh / 2, sgn * half); band.box(bw, bh, 2 * half + bw, sgn * half, h - bh / 2, 0)                                # 水位を示す輪（水面のふち）
    bx, bz = half + .45, half - .6; top = 3.2
    band.ring(.34, .05, bx, h, bz, seg=40)                                                                                                                                   # 目盛り板のまわりの輪
    post.box(.07, top, .05, bx, 0, bz - .03)
    board.quad([bx - .16, 0, bz], [bx + .16, 0, bz], [bx + .16, top, bz], [bx - .16, top, bz]); board.quad([bx + .16, 0, bz - .06], [bx - .16, 0, bz - .06], [bx - .16, top, bz - .06], [bx + .16, top, bz - .06])
    person(man, bx - .85, bz - .1)                                                                                                                                           # 身長1.70mの人（水の中に立つ。札を隠さない位置）
    parts = [(band, dict(name="level", color=[.96, .99, 1, 1], rough=.4)), (post, BODY), (man, BODY), (board, dict(name="ruler", image=ruler(top), rough=.8))]
    for hh, (big, small) in FLOOD.items():                                                                                                                                   # 3つの高さの札（今の水位の札だけ橙）
        pf = Geo(); w = 1.5; x0 = bx + .3; hy = w * 256 / 1024 / 2
        pf.quad([x0, hh - hy, bz + .02], [x0 + w, hh - hy, bz + .02], [x0 + w, hh + hy, bz + .02], [x0, hh + hy, bz + .02]); pf.quad([x0 + w, hh - hy, bz + .008], [x0, hh - hy, bz + .008], [x0, hh + hy, bz + .008], [x0 + w, hh + hy, bz + .008])
        parts.append((pf, dict(name=f"plate{int(hh * 100):03d}", image=plate(big, small, on=abs(hh - h) < 1e-6), rough=.8)))
    post.box(.04, 3.0 + .2, .04, bx + .3 + 1.5 + .02, 0, bz + .014)
    parts += [(side, dict(name="depth", color=[1, 1, 1, 1], image=gradient((70, 170, 185, 70), (10, 60, 90, 190)), blend=True, double=True, rough=.3)),
              (surf, dict(name="surface", color=[1, 1, 1, .66], image=ripple(), blend=True, double=True, rough=.12))]
    return write_glb(path, parts)

# ---------------------------------------------------------------- 書き出し
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); sizes = {}
    sizes["cube_day.glb"], s_day = cube_model(f"{OUT}/cube_day.glb", D["dailyKg"], f"1日分のCO₂　{D['dailyKg']}kg", with_room=True)
    sizes["cube_year.glb"], _ = cube_model(f"{OUT}/cube_year.glb", D["annualT"] * 1000, f"1年分のCO₂　{D['annualT']:.2f}トン")
    pc = D["pcJapan"]
    for age in range(10, 100):
        b = 2026 - age; life_t = sum(pc.get(str(y), pc["2024"]) for y in range(b, b + age))
        sizes[f"cube_life_{age}.glb"], _ = cube_model(f"{OUT}/cube_life_{age}.glb", life_t * 1000, f"{age}歳までのあなたの分")
    for h in (0.5, 1.0, 3.0): sizes[f"flood_{int(h * 100):03d}.glb"] = flood_model(f"{OUT}/flood_{int(h * 100):03d}.glb", h)
    print(f"1日分 {D['dailyKg']}kg・一辺{s_day:.2f}m／{len(sizes)}個・最大 {max(sizes.values()) / 1e6:.3f}MB（{max(sizes, key=sizes.get)}）・合計 {sum(sizes.values()) / 1e6:.1f}MB")
