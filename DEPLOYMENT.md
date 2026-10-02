# Deployment Guide

Retrivance can be deployed on two platforms:
- **Streamlit Cloud** for the SOC dashboard
- **Render** for the FastAPI API

---

## 🚀 Streamlit Cloud (Dashboard)

### Prerequisites
- GitHub account
- Streamlit Cloud account (sign up at [share.streamlit.io](https://share.streamlit.io))

### Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push
   ```

2. **Create new app on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository: `Pragati1466/Retrivance`
   - Select branch: `main`
   - Main file path: `ragsentinel/ui/dashboard.py`
   - Click "Deploy"

3. **Environment Variables (if needed)**
   - No additional environment variables required for basic deployment
   - Streamlit will automatically install dependencies from `requirements.txt`

4. **Access your dashboard**
   - Streamlit will provide a URL like: `https://your-app-name.streamlit.app`

---

## 🌐 Railway (FastAPI API)

### Prerequisites
- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))

### Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push
   ```

2. **Create new Project on Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository: `Pragati1466/Retrivance`
   - Select branch: `main`

3. **Configure Service**
   - Railway will detect it's a Python project
   - Add a new service: "New Service" → "Python"
   - Build command: `pip install -r requirements.txt && pip install -e .`
   - Start command: `uvicorn ragsentinel.api.server:app --host 0.0.0.0 --port $PORT`

4. **Add Persistent Volume (for ChromaDB)**
   - In your service settings
   - Go to "Volumes" section
   - Add a new volume (1GB free tier)
   - Mount path: `/app/data/ledger`

5. **Access your API**
   - Railway will provide a URL like `https://your-app-name.up.railway.app`
   - API docs available at: `https://your-app-name.up.railway.app/docs`

---

## 📦 Alternative: Docker Deployment

For deployment on other platforms (AWS, GCP, Azure, DigitalOcean):

### Build Docker Image
```bash
docker build -t retrivance:latest .
```

### Run Container
```bash
docker run -p 8000:8000 \
  -v $(pwd)/data/ledger:/app/data/ledger \
  retrivance:latest
```

### Push to Container Registry
```bash
# Docker Hub
docker tag retrivance:latest yourusername/retrivance:latest
docker push yourusername/retrivance:latest

# Or use GitHub Container Registry
docker tag retrivance:latest ghcr.io/Pragati1466/retrivance:latest
docker push ghcr.io/Pragati1466/retrivance:latest
```

---

## 🔗 Connecting Dashboard to API

If you deploy both services separately, update the dashboard to point to the deployed API:

In `ragsentinel/ui/dashboard.py`, you may need to configure the API endpoint if the dashboard makes API calls.

---

## 📊 Monitoring

### Streamlit Cloud
- Automatic logging in the Streamlit dashboard
- View logs in the Streamlit Cloud interface

### Render
- Automatic logging in the Render dashboard
- View logs in the Logs tab of your service
- Metrics available in the Metrics tab

---

## 🔒 Security Considerations

- **API Keys**: If you add API keys later, store them as environment variables
- **CORS**: Configure CORS in FastAPI if needed for cross-origin requests
- **Rate Limiting**: Consider adding rate limiting for production use
- **Authentication**: Add authentication to the FastAPI endpoints for production

---

## 🐛 Troubleshooting

### Streamlit Cloud Issues
- **Build fails**: Check `requirements.txt` for compatible versions
- **App crashes**: Check logs in Streamlit Cloud dashboard
- **Dependencies missing**: Ensure all dependencies are in `requirements.txt`

### Render Issues
- **Build fails**: Check Python version compatibility (Python 3.10+)
- **Disk errors**: Ensure persistent disk is mounted correctly
- **Port errors**: Render uses `$PORT` variable automatically
- **Memory errors**: Free tier has 512MB RAM, may need upgrade for larger models

---

## 💰 Cost

- **Streamlit Cloud**: Free tier available
- **Render**: Free tier available (512MB RAM, 0.1 CPU)
- **ChromaDB persistence**: 1GB disk on Render free tier

For production, consider upgrading to paid tiers for better performance.
