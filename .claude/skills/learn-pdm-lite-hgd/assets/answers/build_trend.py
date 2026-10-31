"""Block 1 정답 — 노이즈 vs 추세 판정과 그래프 한 장 대시보드.

현재 폴더(또는 data/)의 Day5_설비센서_50건_가상.csv 를 읽어
outputs/trend_judgement.csv, index.html, expected.json 을 현재 폴더에 만든다.
규칙은 원본을 그대로 따른다.
- 평상 범위: 설비별 하루 전체 평균 ± 2 × 표준편차 (본 강의 덱 ③ 전처리)
- 추세 판정: 처음 12점 기준선의 평균 + 3 × 표준편차를 3번 연속 넘으면 추세 (보충교재 II 프롬프트 3)
"""
import json
from pathlib import Path

import pandas as pd

FILE = "Day5_설비센서_50건_가상.csv"
COLS = ["진동(mm/s)", "온도(℃)", "압력(bar)"]
BASE_N = 12   # 기준선 = 처음 12점(08:00~11:40)
RUN = 3       # 3번 연속 넘으면 추세


def load():
    for p in [Path(FILE), Path("data") / FILE]:
        if p.exists():
            return pd.read_csv(p, encoding="utf-8-sig")
    raise FileNotFoundError(FILE)


def judge(df):
    """설비 × 항목마다 기준선 상한, 상한 초과 점 수, 판정, 추세 시작을 구한다."""
    rows = []
    for eq, g in df.groupby("설비", sort=False):
        g = g.reset_index(drop=True)
        for c in COLS:
            base = g[c].iloc[:BASE_N]
            upper = base.mean() + 3 * base.std()
            over = (g[c] > upper).tolist()
            start, run = None, 0
            for i, o in enumerate(over):
                run = run + 1 if o else 0
                if run == RUN:
                    start = g["시간"].iloc[i - RUN + 1]
                    break
            n = sum(over)
            kind = "추세" if start else ("노이즈" if n else "정상")
            rows.append({"설비": eq, "항목": c, "기준선 상한": round(upper, 3),
                         "상한 초과 점 수": n, "판정": kind, "추세 시작": start or ""})
    return pd.DataFrame(rows)


def first_2sigma(df, eq_prefix):
    """하루 전체 평균 ± 2σ(평상 범위)로 처음 이상 후보가 된 시각."""
    g = df[df["설비"].str.startswith(eq_prefix)]
    hits = []
    for c in COLS:
        m, s = g[c].mean(), g[c].std()
        hits += g.loc[(g[c] > m + 2 * s) | (g[c] < m - 2 * s), "시간"].tolist()
    return min(hits)


def svg_chart(df, b_vib_upper, b_vib_start, a_spike):
    """설비A·B 진동 시간순 선 그래프 한 장 (외부 라이브러리 없이 SVG)."""
    W, H, L, R, T, B = 640, 300, 44, 16, 30, 40
    a = df[df["설비"].str.startswith("설비A")].reset_index(drop=True)
    b = df[df["설비"].str.startswith("설비B")].reset_index(drop=True)
    n, ymax = len(a), 4.0
    x = lambda i: L + i * (W - L - R) / (n - 1)
    y = lambda v: T + (1 - v / ymax) * (H - T - B)
    path = lambda s: " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s))
    vib = COLS[0]
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="설비A·B 진동 선 그래프">']
    for v in [0, 1, 2, 3, 4]:
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{L-8}" y="{y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i in range(0, n, 3):
        parts.append(f'<text x="{x(i):.1f}" y="{H-B+18}" class="ax" text-anchor="middle">{a["시간"][i][11:]}</text>')
    parts.append(f'<line x1="{L}" x2="{W-R}" y1="{y(b_vib_upper):.1f}" y2="{y(b_vib_upper):.1f}" class="upper"/>')
    parts.append(f'<text x="{L+6}" y="{y(b_vib_upper)-8:.1f}" class="lbl up">설비B 진동 기준선 상한 {b_vib_upper:.2f}</text>')
    parts.append(f'<path d="{path(a[vib])}" class="la"/><path d="{path(b[vib])}" class="lb"/>')
    ia = a.index[a["시간"] == a_spike].tolist()[0]
    parts.append(f'<circle cx="{x(ia):.1f}" cy="{y(a[vib][ia]):.1f}" r="5" class="pa"/>'
                 f'<text x="{x(ia)+8:.1f}" y="{y(a[vib][ia])+4:.1f}" class="lbl a">설비A {a_spike[11:]} 한 번의 튐 → 노이즈</text>')
    ib = b.index[b["시간"] == b_vib_start].tolist()[0]
    parts.append(f'<circle cx="{x(ib):.1f}" cy="{y(b[vib][ib]):.1f}" r="5" class="pb"/>'
                 f'<text x="{x(ib)-8:.1f}" y="{y(b[vib][ib])-30:.1f}" class="lbl b" text-anchor="end">설비B 진동 추세 시작 {b_vib_start[11:]}</text>')
    parts.append(f'<text x="{L-8}" y="{T-14}" class="ax" text-anchor="end">mm/s</text></svg>')
    return "".join(parts)


def main():
    df = load()
    tr = judge(df)
    Path("outputs").mkdir(exist_ok=True)
    tr.to_csv("outputs/trend_judgement.csv", index=False, encoding="utf-8-sig")

    pick = lambda eq, c: tr[(tr["설비"].str.startswith(eq)) & (tr["항목"] == c)].iloc[0]
    bt, bv, av = pick("설비B", COLS[1]), pick("설비B", COLS[0]), pick("설비A", COLS[0])
    trends = tr[tr["판정"] == "추세"].sort_values("추세 시작")
    earliest = trends["추세 시작"].iloc[0]
    b2s = first_2sigma(df, "설비B")
    lead = int((pd.to_datetime(b2s) - pd.to_datetime(earliest)).total_seconds() // 60)
    a = df[df["설비"].str.startswith("설비A")]
    a_spike = a.loc[a[COLS[0]] > av["기준선 상한"], "시간"].iloc[0]
    a_spike_v = float(a.loc[a["시간"] == a_spike, COLS[0]].iloc[0])

    summary = (f"설비B(차체 용접로봇 감속기)는 <b>온도가 {bt['추세 시작'][11:]}</b>, "
               f"<b>진동이 {bv['추세 시작'][11:]}</b>부터 추세적으로 올랐다. "
               f"설비A 진동은 {a_spike[11:]}에 한 번 튄 <b>{av['판정']}</b>다. "
               f"추세 시작이 평상 범위(평균 ± 2σ)의 첫 이상 후보({b2s[11:]})보다 <b>{lead}분 빠르다</b>.")
    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>노이즈 vs 추세</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1f2328;--mute:#6b7280;--grid:#e5e7eb;--a:#6b8fb8;--b:#d9622b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e6e3;--mute:#9aa0a6;--grid:#2c3036;--a:#8fb0d6;--b:#f0844f}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Malgun Gothic",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px}}h1{{font-size:1.4rem;margin:0 0 8px}}
.sum{{margin:0 0 16px}}svg{{width:100%;height:auto;display:block}}
.grid{{stroke:var(--grid)}}.ax{{fill:var(--mute);font-size:12px}}.lbl{{font-size:13px;font-weight:600}}
.la{{fill:none;stroke:var(--a);stroke-width:2.5}}.lb{{fill:none;stroke:var(--b);stroke-width:2.5}}
.upper{{stroke:var(--b);stroke-dasharray:6 5;opacity:.8}}.up{{fill:var(--b)}}
.pa{{fill:var(--a)}}.pb{{fill:var(--b)}}.a{{fill:var(--a)}}.b{{fill:var(--b)}}
.key{{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;color:var(--mute);margin:8px 0 0}}
.key i{{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px}}
footer{{margin-top:20px;font-size:13px;color:var(--mute)}}
</style></head><body><main>
<h1>노이즈 vs 추세 — 정비 권고 시점</h1>
<p class="sum">{summary}</p>
{svg_chart(df, bv['기준선 상한'], bv['추세 시작'], a_spike)}
<div class="key"><span><i style="background:var(--a)"></i>설비A 프레스 메인모터 진동</span><span><i style="background:var(--b)"></i>설비B 차체 용접로봇 감속기 진동</span></div>
<footer>기준선 = 처음 12점(08:00~11:40), 상한 = 평균 + 3σ, 3번 연속 넘으면 추세. 센서 값은 실습용 가상 데이터 · 원본 keerhee/kma-auto-genai-3-1 (data/Day5/{FILE})</footer>
</main></body></html>
"""
    Path("index.html").write_text(html, encoding="utf-8")

    vals = {
        "rows": {"value": len(df), "decimals": None, "block": 0},
        "equipment_count": {"value": df["설비"].nunique(), "decimals": None, "block": 0},
        "first_time": {"value": df["시간"].min(), "decimals": None, "block": 0},
        "last_time": {"value": df["시간"].max(), "decimals": None, "block": 0},
        "trend_count": {"value": len(trends), "decimals": None, "block": 1},
        "b_temp_trend_start": {"value": bt["추세 시작"][11:], "decimals": None, "block": 1},
        "b_temp_upper": {"value": float(bt["기준선 상한"]), "decimals": 2, "block": 1},
        "b_vib_trend_start": {"value": bv["추세 시작"][11:], "decimals": None, "block": 1},
        "b_vib_upper": {"value": float(bv["기준선 상한"]), "decimals": 2, "block": 1},
        "a_vib_judgement": {"value": av["판정"], "decimals": None, "block": 1},
        "a_vib_spike_time": {"value": a_spike[11:], "decimals": None, "block": 1},
        "a_vib_spike_value": {"value": a_spike_v, "decimals": 1, "block": 1},
        "b_first_2sigma": {"value": b2s[11:], "decimals": None, "block": 1},
        "lead_minutes": {"value": lead, "decimals": None, "block": 1},
    }
    Path("expected.json").write_text(json.dumps({"values": vals}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(tr.to_string(index=False))
    print(f"가장 이른 추세 시작 {earliest[11:]} · 평상 범위 첫 후보 {b2s[11:]} · {lead}분 빠름")


if __name__ == "__main__":
    main()
