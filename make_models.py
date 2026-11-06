import json, sys, trimesh
from trimesh.visual.material import PBRMaterial

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "data.json", encoding="utf-8"))   # 数値台帳から書き出したデータ
rho = D["densityKgPerM3"]

def box(w, h, d, rgba, x=0.0, z=0.0, y0=0.0):
    """幅w・高さh・奥行d（m）の箱。glTFはYが上なので、底面を y=y0 に置く"""
    m = trimesh.creation.box(extents=[w, h, d])
    m.apply_translation([x, y0 + h / 2, z])
    m.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(
        baseColorFactor=rgba, alphaMode="BLEND" if rgba[3] < 1 else "OPAQUE",
        metallicFactor=0.0, roughnessFactor=0.9, doubleSided=True))
    return m

CO2 = [0.12, 0.37, 0.75, 0.55]                     # デモと同じ青の半透明
cube = lambda kg: box(*(3 * [(kg / rho) ** (1 / 3)]), CO2)

# 体験1：1日分・1年分・これまでの人生（年齢ごと）を実寸の立方体に
cube(D["dailyKg"]).export("cube_day.glb")
cube(D["annualT"] * 1000).export("cube_year.glb")
pc = D["pcJapan"]
for age in range(10, 100):
    b = 2026 - age
    life_t = sum(pc.get(str(y), pc["2024"]) for y in range(b, b + age))
    cube(life_t * 1000).export(f"cube_life_{age}.glb")

# 体験4：部屋の床から水位 h まで水が来た状態（4m四方）＋0.5mごとの目盛りの柱
WATER, SURF = [0.10, 0.35, 0.55, 0.45], [0.55, 0.75, 0.90, 0.85]
for h in (0.5, 1.0, 3.0):
    parts = [box(4.0, h, 4.0, WATER), box(4.0, 0.01, 4.0, SURF, y0=h)]
    for i in range(6):                              # 0〜3mを0.5mずつ色分けした柱
        parts.append(box(0.08, 0.5, 0.08, [0.9, 0.9, 0.9, 1] if i % 2 else [0.2, 0.2, 0.2, 1], x=2.2, y0=0.5 * i))
    trimesh.Scene(parts).export(f"flood_{int(h * 100):03d}.glb")

s = (D["dailyKg"] / rho) ** (1 / 3)
print(f"1日分 {D['dailyKg']}kg・一辺{s:.2f}m")
