"""Retail market dashboard; historical results remain available for audit."""
from pathlib import Path
import streamlit as st
from src.market_dashboard import render

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='M5 市场需求与采购策略研究', layout='wide', page_icon='◈', initial_sidebar_state='collapsed')
render(ROOT)
