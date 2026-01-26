def get_common_styles():
    return """
    <style>
    /* ===== 全体 ===== */
    .main {
        background: linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* ===== サイドバー ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(0, 212, 255, 0.1);
    }
    
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: 1px solid transparent;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(0, 212, 255, 0.1);
        border-color: rgba(0, 212, 255, 0.3);
        color: #00d4ff;
    }
    
    [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {
        color: #ffffff !important;
        background: rgba(0, 212, 255, 0.15) !important;
        border-left: 3px solid #00d4ff !important;
    }
    
    /* ===== カード ===== */
    .cyber-card {
        background: rgba(26, 31, 46, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.05);
        margin-bottom: 1rem;
    }
    
    .cyber-card:hover {
        border-color: rgba(0, 212, 255, 0.4);
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.1);
    }
    
    /* ===== プライマリボタン（押すべきボタン） ===== */
    .stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #00d4ff 0%, #a855f7 100%);
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        color: #0a0f1a;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3),
                    0 0 40px rgba(168, 85, 247, 0.2);
        transition: all 0.3s ease;
    }
    
    .stButton > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.5),
                    0 0 60px rgba(168, 85, 247, 0.3);
        transform: translateY(-2px);
    }
    
    /* ===== セカンダリボタン ===== */
    .stButton > button:not([kind="primary"]) {
        background: rgba(26, 31, 46, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 8px;
        color: #00d4ff;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(0, 212, 255, 0.1);
        border-color: rgba(0, 212, 255, 0.5);
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
    }
    
    /* ===== AIアシスタントボタン ===== */
    [data-testid="stSidebar"] .stButton:last-of-type > button {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d1f3d 100%) !important;
        border: 1px solid rgba(168, 85, 247, 0.4) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        color: #a855f7 !important;
        font-weight: 600 !important;
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stSidebar"] .stButton:last-of-type > button:hover {
        border-color: rgba(168, 85, 247, 0.7) !important;
        box-shadow: 0 0 30px rgba(168, 85, 247, 0.4) !important;
        color: #c084fc !important;
    }
    
    /* ===== ヘッダー ===== */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700;
    }
    
    h1 {
        background: linear-gradient(135deg, #00d4ff 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* ===== テキスト ===== */
    p, span, .stMarkdown {
        color: #94a3b8;
    }
    
    label, .stTextInput label, .stTextArea label, .stSelectbox label {
        color: #cbd5e1 !important;
    }
    
    /* ===== 入力フィールド ===== */
    .stTextInput input, 
    .stTextArea textarea, 
    .stSelectbox > div > div {
        background: rgba(26, 31, 46, 0.8) !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    .stTextInput input:focus, 
    .stTextArea textarea:focus {
        border-color: rgba(0, 212, 255, 0.5) !important;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.2) !important;
    }
    
    /* ===== Expander ===== */
    .streamlit-expanderHeader {
        background: rgba(26, 31, 46, 0.8) !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    /* ===== テーブル ===== */
    .stDataFrame {
        background: rgba(26, 31, 46, 0.8);
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* ===== メトリクス ===== */
    [data-testid="stMetricValue"] {
        color: #00d4ff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
    
    /* ===== 区切り線 ===== */
    hr {
        border-color: rgba(0, 212, 255, 0.2);
    }
    
    /* ===== 成功/警告/エラーメッセージ ===== */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
    
    /* ===== タブ ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(26, 31, 46, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 8px;
        color: #94a3b8;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(0, 212, 255, 0.1) !important;
        border-color: rgba(0, 212, 255, 0.5) !important;
        color: #00d4ff !important;
    }
    
    /* ===== プログレスバー ===== */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
    }
    
    /* ===== スピナー ===== */
    .stSpinner > div {
        border-top-color: #00d4ff !important;
    }
    </style>
    """

def apply_styles():
    import streamlit as st
    st.markdown(get_common_styles(), unsafe_allow_html=True)

def page_header(title, subtitle=None):
    """ページヘッダー（グラデーションタイトル）"""
    import streamlit as st
    st.markdown(f'<h1 style="font-size: 2rem; margin-bottom: 0.5rem;">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p style="color: #64748b; margin-bottom: 2rem;">{subtitle}</p>', unsafe_allow_html=True)

def cyber_card(content):
    """サイバー感のあるカード"""
    return f'<div class="cyber-card">{content}</div>'
