FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Windows checkouts can add CRLF line endings, which break shell scripts
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
CMD ["sh", "start.sh"]
