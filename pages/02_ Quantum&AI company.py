import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="주식 데이터 시각화",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# 회사 목록 정의
COMPANIES = {
    "미국 대형주": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "NVIDIA": "NVDA",
        "Tesla": "TSLA",
        "Meta": "META",
        "Netflix": "NFLX",
        "Adobe": "ADBE",
        "Salesforce": "CRM"
    },
    "AI/반도체": {
        "NVIDIA": "NVDA",
        "AMD": "AMD",
        "Intel": "INTL",
        "Qualcomm": "QCOM",
        "Broadcom": "AVGO",
        "Palantir": "PLTR",
        "C3.ai": "AI",
        "SoundHound AI": "SOUN"
    },
    "전기차/배터리": {
        "Tesla": "TSLA",
        "BYD": "BYDDY",
        "NIO": "NIO",
        "XPeng": "XPEV",
        "Li Auto": "LI",
        "Rivian": "RIVN",
        "Lucid Motors": "LCID"
    },
    "한국 주요 기업": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "LG화학": "051910.KS",
        "현대차": "005380.KS",
        "기아": "000270.KS"
    }
}

@st.cache_data(ttl=300)  # 5분 캐시
def get_stock_data(ticker, period="1y"):
    """주식 데이터를 가져오는 함수"""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        if data.empty:
            return None
        return data
    except Exception as e:
        st.error(f"❌ {ticker} 데이터 로딩 실패: {str(e)}")
        return None

@st.cache_data(ttl=300)
def get_company_info(ticker):
    """회사 정보를 가져오는 함수"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'marketCap': info.get('marketCap', 0),
            'currentPrice': info.get('currentPrice', 0),
            'previousClose': info.get('previousClose', 0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0)
        }
    except Exception as e:
        st.warning(f"⚠️ {ticker} 회사 정보 로딩 실패: {str(e)}")
        return {
            'name': ticker,
            'sector': 'N/A',
            'marketCap': 0,
            'currentPrice': 0,
            'previousClose': 0,
            'fiftyTwoWeekHigh': 0,
            'fiftyTwoWeekLow': 0
        }

def format_number(num):
    """숫자를 읽기 쉬운 형태로 변환"""
    if num >= 1e12:
        return f"${num/1e12:.2f}T"
    elif num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    elif num >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"

def calculate_performance(data):
    """성과 지표 계산"""
    if data is None or data.empty:
        return {}
    
    start_price = data['Close'].iloc[0]
    end_price = data['Close'].iloc[-1]
    total_return = ((end_price - start_price) / start_price) * 100
    
    # 변동성 계산 (일별 수익률의 표준편차)
    daily_returns = data['Close'].pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) * 100  # 연간 변동성
    
    return {
        'start_price': start_price,
        'end_price': end_price,
        'total_return': total_return,
        'max_price': data['Close'].max(),
        'min_price': data['Close'].min(),
        'volatility': volatility,
        'avg_volume': data['Volume'].mean()
    }

def main():
    # 헤더
    st.markdown('<h1 class="main-header">📈 주식 데이터 시각화 대시보드</h1>', unsafe_allow_html=True)
    
    # 사이드바 설정
    st.sidebar.title("🎯 설정")
    
    # 기업 선택
    st.sidebar.subheader("기업 선택")
    
    # 카테고리별 기업 표시
    selected_companies = {}
    for category, companies in COMPANIES.items():
        st.sidebar.write(f"**{category}**")
        for company, ticker in companies.items():
            if st.sidebar.checkbox(f"{company} ({ticker})", key=f"{category}_{ticker}"):
                selected_companies[company] = ticker
    
    # 기간 선택
    st.sidebar.subheader("📅 분석 기간")
    period_options = {
        "1개월": "1mo",
        "3개월": "3mo",
        "6개월": "6mo",
        "1년": "1y",
        "2년": "2y",
        "5년": "5y"
    }
    
    selected_period = st.sidebar.selectbox(
        "기간을 선택하세요:",
        options=list(period_options.keys()),
        index=3  # 기본값: 1년
    )
    
    # 차트 타입 선택
    st.sidebar.subheader("📊 차트 옵션")
    chart_type = st.sidebar.radio(
        "차트 타입:",
        ["라인 차트", "캔들스틱 차트", "비교 차트"]
    )
    
    show_volume = st.sidebar.checkbox("거래량 표시", value=True)
    show_ma = st.sidebar.checkbox("이동평균선 표시", value=False)
    
    if not selected_companies:
        st.warning("⚠️ 분석할 기업을 선택해주세요.")
        st.info("👈 왼쪽 사이드바에서 기업을 선택하세요.")
        return
    
    # 데이터 로딩
    with st.spinner("📊 데이터를 불러오는 중..."):
        stock_data = {}
        company_info = {}
        
        progress_bar = st.progress(0)
        for i, (company, ticker) in enumerate(selected_companies.items()):
            progress_bar.progress((i + 1) / len(selected_companies))
            
            data = get_stock_data(ticker, period_options[selected_period])
            info = get_company_info(ticker)
            
            if data is not None:
                stock_data[company] = data
                company_info[company] = info
        
        progress_bar.empty()
    
    if not stock_data:
        st.error("❌ 선택한 기업의 데이터를 불러올 수 없습니다.")
        return
    
    # 회사 정보 카드
    st.subheader("💼 선택된 기업 정보")
    
    # 반응형 열 생성
    num_cols = min(len(selected_companies), 4)
    cols = st.columns(num_cols)
    
    for i, (company, info) in enumerate(company_info.items()):
        with cols[i % num_cols]:
            current_price = info['currentPrice']
            previous_close = info['previousClose']
            change = current_price - previous_close if previous_close else 0
            change_pct = (change / previous_close * 100) if previous_close else 0
            
            # 색상 결정
            color = "🟢" if change >= 0 else "🔴"
            
            st.markdown(f"""
            <div class="metric-container">
                <h4>{company}</h4>
                <h2>{format_number(current_price).replace('$', '$')}</h2>
                <p>{color} {change:+.2f} ({change_pct:+.2f}%)</p>
                <p>시총: {format_number(info['marketCap'])}</p>
                <p>섹터: {info['sector']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 주가 차트
    st.subheader("📈 주가 차트")
    
    if chart_type == "라인 차트":
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        
        for i, (company, data) in enumerate(stock_data.items()):
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['Close'],
                mode='lines',
                name=company,
                line=dict(color=colors[i % len(colors)], width=3),
                hovertemplate=f'<b>{company}</b><br>' +
                               'Date: %{x}<br>' +
                               'Price: $%{y:.2f}<br>' +
                               '<extra></extra>'
            ))
            
            # 이동평균선 추가
            if show_ma:
                ma20 = data['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=ma20,
                    mode='lines',
                    name=f'{company} MA20',
                    line=dict(color=colors[i % len(colors)], width=1, dash='dash'),
                    opacity=0.7
                ))
        
        fig.update_layout(
            title=f"주가 추이 - {selected_period}",
            xaxis_title="날짜",
            yaxis_title="주가 (USD)",
            hovermode='x unified',
            height=600,
            template='plotly_white',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "캔들스틱 차트":
        if len(selected_companies) > 1:
            st.info("💡 캔들스틱 차트는 한 번에 하나의 기업만 표시됩니다.")
            selected_company = st.selectbox("표시할 기업을 선택하세요:", list(selected_companies.keys()))
        else:
            selected_company = list(selected_companies.keys())[0]
        
        data = stock_data[selected_company]
        
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=selected_company,
            increasing_line_color='#00ff00',
            decreasing_line_color='#ff0000'
        ))
        
        # 이동평균선 추가
        if show_ma:
            ma20 = data['Close'].rolling(window=20).mean()
            ma50 = data['Close'].rolling(window=50).mean()
            
            fig.add_trace(go.Scatter(
                x=data.index, y=ma20,
                mode='lines', name='MA20',
                line=dict(color='orange', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=data.index, y=ma50,
                mode='lines', name='MA50',
                line=dict(color='purple', width=2)
            ))
        
        fig.update_layout(
            title=f"{selected_company} 캔들스틱 차트 - {selected_period}",
            xaxis_title="날짜",
            yaxis_title="주가 (USD)",
            height=600,
            template='plotly_white',
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:  # 비교 차트
        # 정규화된 가격 (시작점을 100으로 설정)
        fig = go.Figure()
        colors = px.colors.qualitative.Set1
        
        for i, (company, data) in enumerate(stock_data.items()):
            normalized_price = (data['Close'] / data['Close'].iloc[0]) * 100
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=normalized_price,
                mode='lines',
                name=company,
                line=dict(color=colors[i % len(colors)], width=3),
                hovertemplate=f'<b>{company}</b><br>' +
                               'Date: %{x}<br>' +
                               'Normalized: %{y:.2f}<br>' +
                               '<extra></extra>'
            ))
        
        fig.update_layout(
            title=f"주가 비교 (정규화) - {selected_period}",
            xaxis_title="날짜",
            yaxis_title="정규화된 가격 (시작점=100)",
            hovermode='x unified',
            height=600,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 거래량 차트
    if show_volume:
        st.subheader("📊 거래량 분석")
        
        fig_volume = go.Figure()
        
        for i, (company, data) in enumerate(stock_data.items()):
            fig_volume.add_trace(go.Scatter(
                x=data.index,
                y=data['Volume'],
                mode='lines',
                name=company,
                line=dict(color=colors[i % len(colors)], width=2),
                fill='tonexty' if i > 0 else 'tozeroy',
                fillcolor=colors[i % len(colors)],
                opacity=0.3
            ))
        
        fig_volume.update_layout(
            title=f"거래량 추이 - {selected_period}",
            xaxis_title="날짜",
            yaxis_title="거래량",
            hovermode='x unified',
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_volume, use_container_width=True)
    
    # 성과 분석 테이블
    st.subheader("📊 성과 분석")
    
    performance_data = []
    for company, data in stock_data.items():
        perf = calculate_performance(data)
        if perf:
            performance_data.append({
                '기업': company,
                '시작가': f"${perf['start_price']:.2f}",
                '현재가': f"${perf['end_price']:.2f}",
                '수익률': f"{perf['total_return']:.2f}%",
                '최고가': f"${perf['max_price']:.2f}",
                '최저가': f"${perf['min_price']:.2f}",
                '연간 변동성': f"{perf['volatility']:.2f}%",
                '평균 거래량': f"{perf['avg_volume']:,.0f}"
            })
    
    if performance_data:
        df_performance = pd.DataFrame(performance_data)
        
        # 수익률에 따른 색상 적용
        def highlight_returns(val):
            if '수익률' in val.name:
                color = 'lightgreen' if float(val.replace('%', '')) > 0 else 'lightcoral'
                return [f'background-color: {color}' for _ in val]
            return ['' for _ in val]
        
        st.dataframe(
            df_performance.style.apply(highlight_returns, axis=0),
            use_container_width=True
        )
    
    # 통계 요약
    st.subheader("📈 주요 통계")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if performance_data:
            best_performer = max(performance_data, key=lambda x: float(x['수익률'].replace('%', '')))
            st.metric(
                "최고 수익률",
                best_performer['기업'],
                best_performer['수익률']
            )
    
    with col2:
        if performance_data:
            returns = [float(x['수익률'].replace('%', '')) for x in performance_data]
            avg_return = np.mean(returns)
            st.metric(
                "평균 수익률",
                f"{avg_return:.2f}%",
                f"{'상승' if avg_return > 0 else '하락'}"
            )
    
    with col3:
        if performance_data:
            volatilities = [float(x['연간 변동성'].replace('%', '')) for x in performance_data]
            avg_volatility = np.mean(volatilities)
            st.metric(
                "평균 변동성",
                f"{avg_volatility:.2f}%",
                "연간 기준"
            )
    
    # 면책 조항
    st.markdown("---")
    st.markdown("""
    ### ⚠️ 투자 유의사항
    
    - 이 대시보드는 교육 및 정보 제공 목적으로만 사용됩니다.
    - 투자 결정은 본인의 판단과 책임하에 이루어져야 합니다.
    - 과거 성과가 미래 성과를 보장하지 않습니다.
    - 실제 투자 전에 전문가와 상담하시기 바랍니다.
    
    **데이터 출처**: Yahoo Finance
    """)

if __name__ == "__main__":
    main()
