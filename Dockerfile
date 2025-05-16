FROM python:3.10-slim
COPY . /backend
WORKDIR /backend
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8000
COPY . .
CMD ["python", "main.py"]