"""data.json を作る。Our World in Data（owid-co2-data.csv）と気象庁の猛暑日データ（hotdays.py）から。"""
import json, sys, pandas as pd
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from hotdays import HOT, HOMOG_FROM, RELOCATION_NOTE
df = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "owid-co2-data.csv")
jp = df[(df.country == "Japan") & df.year.between(1920, 2024)].dropna(subset=["co2_per_capita"])
pc = {str(int(y)): round(v, 3) for y, v in zip(jp.year, jp.co2_per_capita)}
w = df[(df.country == "World") & (df.year <= 2024)][["year", "co2"]].dropna()
share = {str(a): round(w[w.year < 2026 - a].co2.sum() / w.co2.sum(), 3) for a in range(10, 100)}
hot = {s: {str(y): v for y, v in d.items() if y >= HOMOG_FROM[s]} for s, d in HOT.items()}
data = {
    "asOf": "2026-11-05",
    "annualT": pc["2024"], "dailyKg": round(pc["2024"] * 1000 / 365, 1), "densityKgPerM3": 1.84,
    "sector": {"household": 0.16, "outside": 0.84},
    "shareAtBirthWorld": share, "pcJapan": pc,
    "hotDays": hot,
    "stationName": {"osaka": "大阪", "kyoto": "京都", "nagoya": "名古屋", "fukuoka": "福岡", "tokyo": "東京", "sapporo": "札幌", "sendai": "仙台", "niigata": "新潟", "hiroshima": "広島", "kagoshima": "鹿児島"},
    "stationOfRegion": {"hokkaido": "sapporo", "tohoku": "sendai", "kanto": "tokyo", "hokuriku": "niigata", "tokai": "nagoya", "kinki": "osaka", "chugoku": "hiroshima", "shikoku": "hiroshima", "kyushu_n": "fukuoka", "kyushu_s": "kagoshima", "amami": "kagoshima"},
    "regionNote": {"shikoku": "四国地方には対象の大都市がないため、近い広島の値です。", "amami": "奄美地方の代わりに鹿児島の値です。", "okinawa": "沖縄地方には対象の大都市がないため、大阪の値です。"},
    "relocationNote": RELOCATION_NOTE,
    "defaultStation": "osaka",
    "sources": [
        {"id": "owid", "label": "Our World in Data CO2 and Greenhouse Gas Emissions (Global Carbon Project)", "url": "https://github.com/owid/co2-data", "accessed": "2026-11-05"},
        {"id": "jma", "label": "気象庁 大都市における猛暑日日数の長期変化傾向（年別値）", "url": "https://www.data.jma.go.jp/cpdinfo/himr/himr_tmaxGE35.html", "accessed": "2026-11-05"},
    ],
}
json.dump(data, open("data/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(data["dailyKg"], share["20"], len(hot["osaka"]))
