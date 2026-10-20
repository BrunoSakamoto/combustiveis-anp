FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "duckdb>=1.4,<2" "streamlit>=1.45,<2" "plotly>=6,<8" "pandas>=2.2"
EXPOSE 8501
CMD ["streamlit", "run", "painel/app.py", "--server.address=0.0.0.0", "--server.headless=true"]
