import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# ---------------------------------------------------------
# 1. 데이터 로드 및 전처리 (이전과 동일한 로직)
# ---------------------------------------------------------
@st.cache_data
def load_and_process_data():
    file_path = '지역별_신·재생에너지_발전량_비재생폐기물_제외__2019년_4_4분기__20260129144751.xlsx - 데이터.csv'
    
    # 헤더가 복잡하므로 header=None으로 불러와서 직접 파싱
    df_raw = pd.read_csv(file_path, header=None)
    
    # 2023년 데이터 컬럼 인덱스 (분석된 위치)
    col_map = {
        '태양광': 33, '풍력': 42, '수력': 51, '해양': 60, 
        '바이오': 66, '폐기물': 147, '연료전지': 207, 'IGCC': 216
    }
    
    regions = df_raw.iloc[3:, 0].values
    data = {'Region': regions}
    
    for src, col_idx in col_map.items():
        raw_vals = df_raw.iloc[3:, col_idx].values
        clean_vals = []
        for v in raw_vals:
            if isinstance(v, str):
                v = v.replace(',', '').replace('-', '0')
            try:
                clean_vals.append(float(v))
            except:
                clean_vals.append(0)
        data[src] = clean_vals
        
    df = pd.DataFrame(data)
    df = df[df['Region'] != '전국'] # 전국 합계 제외
    
    # 좌표 데이터 매핑
    lat_lon = {
        '서울': [37.5665, 126.9780], '부산': [35.1796, 129.0756], '대구': [35.8714, 128.6014],
        '인천': [37.4563, 126.7052], '광주': [35.1595, 126.8526], '대전': [36.3504, 127.3845],
        '울산': [35.5384, 129.3114], '세종': [36.4800, 127.2890], '경기': [37.4138, 127.5183],
        '강원': [37.65, 128.45], '충북': [36.8, 127.7], '충남': [36.5, 126.8],
        '전북': [35.8, 127.1], '전남': [34.9, 126.95], '경북': [36.4, 128.8],
        '경남': [35.4, 128.5], '제주': [33.40, 126.55]
    }
    
    df['lat'] = df['Region'].map(lambda x: lat_lon.get(x, [0,0])[0])
    df['lon'] = df['Region'].map(lambda x: lat_lon.get(x, [0,0])[1])
    
    # 총 발전량 계산 (마커 크기용)
    df['Total'] = df[list(col_map.keys())].sum(axis=1)
    
    return df, list(col_map.keys())

# ---------------------------------------------------------
# 2. 메인 앱 로직
# ---------------------------------------------------------
def main():
    st.set_page_config(layout="wide") # 넓은 화면 사용
    st.title("🇰🇷 지역별 신재생에너지 상세 분석 대시보드")
    st.markdown("지도의 **마커를 클릭**하면 우측에 상세 발전량이 표시됩니다.")

    try:
        df, sources = load_and_process_data()
        
        # 화면 레이아웃 분할 (왼쪽: 지도, 오른쪽: 상세 차트)
        col_map, col_detail = st.columns([1.2, 1])

        with col_map:
            st.subheader("📍 지역 선택")
            
            # 지도 생성
            m = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles="cartodbpositron")
            
            # 마커 추가
            for i, row in df.iterrows():
                # 총 발전량에 따른 마커 크기 및 색상
                radius = (row['Total'] / df['Total'].max()) * 25 + 5
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=radius,
                    color='#FF4B4B',
                    fill=True,
                    fill_color='#FF4B4B',
                    fill_opacity=0.6,
                    tooltip=row['Region'], # 마우스 올렸을 때 이름 표시
                    popup=row['Region']    # 클릭 식별자 (중요)
                ).add_to(m)

            # 지도 출력 및 클릭 이벤트 리턴 받기
            # last_object_clicked_popup을 통해 클릭된 마커의 팝업 텍스트(지역명)를 가져옴
            map_output = st_folium(m, width="100%", height=600)

        with col_detail:
            st.subheader("📊 상세 발전 현황")
            
            selected_region = None
            
            # 지도 클릭 감지 로직
            if map_output['last_object_clicked_popup']:
                selected_region = map_output['last_object_clicked_popup']
            
            if selected_region:
                # 선택된 지역 데이터 필터링
                region_data = df[df['Region'] == selected_region].iloc[0]
                
                st.markdown(f"### **{selected_region}** 에너지 믹스")
                
                # 데이터 가공 (Plotly 차트용)
                chart_data = pd.DataFrame({
                    '에너지원': sources,
                    '발전량(MWh)': [region_data[src] for src in sources]
                })
                # 0인 값 제외 (깔끔한 차트를 위해)
                chart_data = chart_data[chart_data['발전량(MWh)'] > 0]
                
                # 1. 파이 차트 (비중 확인용)
                fig_pie = px.pie(
                    chart_data, 
                    values='발전량(MWh)', 
                    names='에너지원',
                    title=f"{selected_region} 발전 비중",
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # 2. 막대 차트 (수치 비교용)
                fig_bar = px.bar(
                    chart_data, 
                    x='에너지원', 
                    y='발전량(MWh)',
                    text_auto='.2s',
                    title=f"{selected_region} 발전량 규모",
                    color='에너지원'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # 3. 텍스트 요약
                top_source = chart_data.sort_values(by='발전량(MWh)', ascending=False).iloc[0]
                st.info(f"💡 **{selected_region}**의 주력 에너지원은 **{top_source['에너지원']}**이며, "
                        f"전체 발전량은 약 **{int(region_data['Total']):,} MWh**입니다.")
                
            else:
                st.info("👈 지도에서 원하는 지역(빨간 원)을 클릭해주세요.")
                st.write("지역을 클릭하면 상세 데이터가 이곳에 표시됩니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
