import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Check for saved user on app load
const savedUserId = localStorage.getItem('user_id');
if (savedUserId) {
  api.defaults.headers.common['x-user-id'] = savedUserId;
}

// Expose basic fetchers
export const getPortfolio = () => api.get('/portfolio').then(r => r.data);
export const getAnalytics = () => api.get('/portfolio/analytics').then(r => r.data);
export const getNews = () => api.get('/market/news').then(r => r.data);
export const generateNBA = () => api.post('/nba/generate').then(r => r.data);
export const getNBAHistory = () => api.get('/nba/history').then(r => r.data);
export const getAlerts = () => api.get('/alerts').then(r => r.data);
export const sendChat = (message) => api.post('/chat', { message }).then(r => r.data);
export const getChatHistory = () => api.get('/chat/history').then(r => r.data);

// Event-driven NBA
export const fetchEvents = (maxArticles = 20) => api.get(`/events/fetch?max_articles=${maxArticles}`).then(r => r.data);
export const scanEvents = () => api.post('/events/scan').then(r => r.data);
export const startPolling = () => api.post('/events/polling/start').then(r => r.data);
export const stopPolling = () => api.post('/events/polling/stop').then(r => r.data);
export const getPollingStatus = () => api.get('/events/polling/status').then(r => r.data);
