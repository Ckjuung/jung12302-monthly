
import requests, xmltodict, pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

today = datetime.date(2025, 4, 1)
start_date = today - relativedelta(months=1)
end_date = today - datetime.timedelta(days=1)
target_month = start_date.strftime("%Y%m")

service_key = "DBL9%2FjevAhTCfpDi5RqbnF61jt1lxJGlxxUSW%2F7mv4GB9bDJk6F1V%2B2izfb51UFSFtAGXxQ89Xy89pk4VFOMuQ%3D%3D"
gu_list = {
    "강남구": "11680", "서초구": "11650", "송파구": "11710", "성동구": "11200",
    "동작구": "11590", "광진구": "11215", "동대문구": "11230", "마포구": "11440", "강동구": "11740"
}
url_base = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

all_data = []
for gu, code in gu_list.items():
    url = f"{url_base}?serviceKey={service_key}&LAWD_CD={code}&DEAL_YMD={target_month}&numOfRows=1000"
    try:
        r = requests.get(url)
        parsed = xmltodict.parse(r.content)
        items = parsed.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if items:
            if isinstance(items, dict): items = [items]
            for item in items:
                item['sggNm'] = gu
                all_data.append(item)
    except Exception as e:
        print(f"❗ {gu} 요청 실패: {e}")
        continue

# ✅ 응답 비었을 경우 중단
if not all_data:
    raise ValueError("🚫 API로부터 수신된 거래 데이터가 없습니다. 분석을 중단합니다.")

df = pd.DataFrame(all_data)

# ✅ 'sggNm' 컬럼이 없는 경우 중단
if 'sggNm' not in df.columns:
    raise ValueError("🚨 'sggNm' 컬럼이 포함된 데이터가 없습니다. API 응답이 비어 있거나 잘못됨.")

# 전처리
for col in ['dealYear', 'dealMonth', 'dealDay', 'excluUseAr', 'dealAmount', 'dealingGbn', 'sggNm']:
    if col not in df.columns: df[col] = None
df['거래일'] = pd.to_datetime(df['dealYear'] + df['dealMonth'].str.zfill(2) + df['dealDay'].str.zfill(2), errors='coerce')
df = df[(df['거래일'] >= pd.Timestamp(start_date)) & (df['거래일'] <= pd.Timestamp(end_date))]
df['excluUseAr'] = pd.to_numeric(df['excluUseAr'], errors='coerce')
df['거래금액(만원)'] = df['dealAmount'].str.replace(",", "").astype(int)
df = df[df['dealingGbn'] == '중개거래']

def classify_group(area):
    if 50.0 <= area < 60.0: return '그룹1 (50~60㎡)'
    elif 80.0 <= area <= 85.0: return '그룹2 (80~85㎡)'
    else: return None

df['면적그룹'] = df['excluUseAr'].apply(classify_group)
df = df[df['면적그룹'].notnull()]

lines = []
lines.append(f"# 📊 {start_date.strftime('%Y년 %m월')} 실거래가 보고서 (전용면적 그룹별 Top3)\n")

for idx, gu in enumerate(gu_list, start=1):
    lines.append(f"## {idx}. {gu}")
    df_gu = df[df['sggNm'] == gu]
    for group in ['그룹1 (50~60㎡)', '그룹2 (80~85㎡)']:
        df_grp = df_gu[df_gu['면적그룹'] == group]
        if df_grp.empty:
            lines.append(f"- **{group}**: 거래 없음\n")
            continue
        lines.append(f"\n- **{group}**")
        top3 = (
            df_grp.groupby('aptNm')
            .agg(거래건수=('거래일', 'count'))
            .sort_values('거래건수', ascending=False)
            .head(3)
            .reset_index()
        )
        for i, row in top3.iterrows():
            apt = row['aptNm']
            count = row['거래건수']
            df_apt = df_grp[df_grp['aptNm'] == apt]
            avg = round(df_apt['거래금액(만원)'].mean())
            maxp = df_apt['거래금액(만원)'].max()
            minp = df_apt['거래금액(만원)'].min()
            lines.append(f"    - {i+1}위: {apt} ({count}건, 평균 {avg:,}만원, 최고가 {maxp:,}만원, 최저가 {minp:,}만원)")

with open(f"report_{start_date.strftime('%Y_%m')}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
