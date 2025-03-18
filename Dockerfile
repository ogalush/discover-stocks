FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Streamlitアプリをコピー
COPY . .

# ポートを指定
EXPOSE 8501

# Streamlitアプリの起動
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
