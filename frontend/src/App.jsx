import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import NBA from './pages/NBA';
import NBAHistory from './pages/NBAHistory';
import MarketFeed from './pages/MarketFeed';
import AIChat from './pages/AIChat';
import SectorOverview from './pages/SectorOverview';
import SectorDrillDown from './pages/SectorDrillDown';
import StockIntelligence from './pages/StockIntelligence';
import Onboarding from './pages/Onboarding';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Simulation from './pages/Simulation';

import { Activity, BarChart2, Zap, Globe, MessageSquare, Menu, Bell, LogOut, User as UserIcon, PieChart, GitBranch, Moon, Sun, Settings, Search, Shield } from 'lucide-react';
import clsx from 'clsx';
import { api } from './api/client';
import { ThemeProvider } from './components/ThemeProvider';
import { useTheme } from './hooks/use-theme';

export default function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <Router>
        <AppContent />
      </Router>
    </ThemeProvider>
  );
}

function AppContent() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  const isAuthPage = location.pathname === '/login' || location.pathname === '/signup';

  useEffect(() => {
    const initAuth = async () => {
      const currentPath = location.pathname;
      const isCurrentAuthPage = currentPath === '/login' || currentPath === '/signup';
      
      const savedUserId = localStorage.getItem('user_id');
      
      if (savedUserId) {
        api.defaults.headers.common['x-user-id'] = savedUserId;
        try {
          await api.get('/auth/me');
          const alertsRes = await api.get('/alerts');
          setAlerts(alertsRes.data);
        } catch {
          localStorage.removeItem('user_id');
          localStorage.removeItem('user_name');
          if (!isCurrentAuthPage) navigate('/login');
        }
      } else if (!isCurrentAuthPage) {
        navigate('/login');
      }
      setLoading(false);
    };
    
    initAuth();
  }, [location.pathname, navigate]);

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    api.defaults.headers.common['x-user-id'] = '';
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (isAuthPage) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Routes>
          <Route path="/login" element={<Login onLoginSuccess={() => {}} />} />
          <Route path="/signup" element={<Signup />} />
        </Routes>
        <Toaster position="bottom-right" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background text-foreground font-sans selection:bg-primary/20 selection:text-primary overflow-hidden">
      <Sidebar className="w-64 flex-shrink-0 hidden md:flex flex-col z-20" />
      
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        <TopBar 
          unreadAlerts={alerts.filter(a => !a.is_read).length} 
          onLogout={handleLogout}
          showUserMenu={showUserMenu}
          setShowUserMenu={setShowUserMenu}
        />
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background p-6 custom-scrollbar scroll-smooth">
          <div className="max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/nba" element={<NBA />} />
              <Route path="/nba-history" element={<NBAHistory />} />
              <Route path="/market" element={<MarketFeed />} />
              <Route path="/chat" element={<AIChat />} />
              <Route path="/sector-overview" element={<SectorOverview />} />
              <Route path="/sector/:ticker" element={<SectorDrillDown />} />
              <Route path="/stock/:ticker" element={<StockIntelligence />} />
              <Route path="/simulation" element={<Simulation />} />
            </Routes>
          </div>
        </main>
      </div>
      <Toaster position="bottom-right" />
    </div>
  );
}

function Sidebar({ className }) {
  const location = useLocation();
  const { theme, setTheme } = useTheme();
  
  const navs = [
    { name: "Dashboard", path: "/", icon: Activity },
    { name: "Portfolio", path: "/portfolio", icon: BarChart2 },
    { name: "Sector Overview", path: "/sector-overview", icon: PieChart },
    { name: "Next Best Action", path: "/nba", icon: Zap },
    { name: "NBA History", path: "/nba-history", icon: Zap },
    { name: "What-If Sim", path: "/simulation", icon: GitBranch },
    { name: "Market Intel", path: "/market", icon: Globe },
    { name: "AI Chat", path: "/chat", icon: MessageSquare },
  ];

  return (
    <div className={clsx(className, "bg-card border-r border-border shadow-xl shadow-black/5")}>
      <div className="p-6 flex items-center justify-between mb-2">
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/25 group-hover:scale-105 transition-all">
            <Activity className="text-primary-foreground" size={20} />
          </div>
          <div>
            <span className="text-foreground font-bold text-xl tracking-tight block leading-none uppercase">WealthAI</span>
            <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-widest">Intelligence</span>
          </div>
        </Link>
      </div>
      
      <nav className="flex-1 px-3 space-y-1 mt-4 overflow-y-auto custom-scrollbar">
        {navs.map(n => {
          const Icon = n.icon;
          const isActive = location.pathname === n.path;
          return (
            <Link key={n.name} to={n.path}
              className={clsx("flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-all font-medium text-sm group relative", 
                isActive 
                  ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon size={18} className={clsx("transition-colors", isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground")} />
              <span>{n.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 mx-3 mb-4 rounded-xl bg-accent/50 border border-border/50">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Appearance</span>
          <button 
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-1.5 rounded-md bg-background border border-border hover:bg-accent transition-colors shadow-sm"
          >
            {theme === 'dark' ? <Sun size={14} className="text-amber-400" /> : <Moon size={14} className="text-blue-500" />}
          </button>
        </div>
        
        <div className="flex items-center space-x-3 p-1">
          <div className="flex-1 h-1.5 bg-background rounded-full overflow-hidden border border-border/50">
            <div className="bg-bullish w-full h-full rounded-full animate-pulse-slow"></div>
          </div>
          <span className="text-[10px] font-mono text-bullish uppercase">System OK</span>
        </div>
      </div>
    </div>
  );
}

function TopBar({ unreadAlerts, onLogout, showUserMenu, setShowUserMenu }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [tickerSuggestions, setTickerSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const userName = localStorage.getItem('user_name') || 'Investor';
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  const navigate = useNavigate();
  const searchRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const searchTickers = async (query) => {
    if (query.length < 2) {
      setTickerSuggestions([]);
      return;
    }
    try {
      const res = await api.get(`/ticker/search?q=${encodeURIComponent(query)}`);
      setTickerSuggestions(res.data);
    } catch {
      setTickerSuggestions([]);
    }
  };

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    setShowSuggestions(true);
    searchTickers(val);
  };

  const selectSuggestion = (s) => {
    setSearchQuery(s.symbol);
    setTickerSuggestions([]);
    setShowSuggestions(false);
    navigate(`/stock/${s.symbol}`);
  };

  return (
    <header className="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b border-border bg-card/50 backdrop-blur-md sticky top-0 z-10">
      <div className="md:hidden flex flex-1">
        <Menu className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors" />
      </div>
      
      <div className="hidden md:flex flex-1 items-center">
        <div className="relative w-96 group" ref={searchRef}>
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <Search size={16} className="text-muted-foreground group-focus-within:text-primary transition-colors" />
          </div>
          <input 
            type="text" 
            placeholder="Search assets, sectors, intelligence..." 
            value={searchQuery}
            onChange={handleSearchChange}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && searchQuery.trim()) {
                navigate(`/stock/${searchQuery.trim().toUpperCase()}`);
                setSearchQuery('');
                setShowSuggestions(false);
              }
            }}
            onFocus={() => searchQuery.length >= 2 && setShowSuggestions(true)}
            className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none transition-all duration-300 shadow-sm" 
          />
          {showSuggestions && tickerSuggestions.length > 0 && (
            <div className="absolute z-50 w-full mt-2 bg-card border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
               <div className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase bg-accent/50 border-b border-border">Market Assets</div>
              {tickerSuggestions.map((s) => (
                <div key={s.symbol} onClick={() => selectSuggestion(s)} 
                     className="px-4 py-3 hover:bg-accent cursor-pointer text-sm border-b border-border last:border-b-0 flex items-center justify-between group">
                  <div className="flex flex-col">
                    <span className="font-bold text-foreground group-hover:text-primary transition-colors uppercase tracking-tight">{s.symbol}</span>
                    <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors line-clamp-1 uppercase tracking-tighter">{s.name}</span>
                  </div>
                  <Zap size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-all transform group-hover:scale-110" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <button className="relative p-2.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded-xl transition-all">
          <Bell size={20} />
          {unreadAlerts > 0 && <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-bearish border-2 border-background rounded-full animate-pulse"></span>}
        </button>
        
        <div className="relative">
          <button 
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center space-x-3 pl-3 pr-2 py-1.5 rounded-2xl border border-transparent hover:border-border hover:bg-accent transition-all active:scale-95"
          >
            <div className="flex flex-col items-end hidden sm:flex leading-none">
              <span className="text-sm font-bold text-foreground leading-none mb-0.5">{userName.split(' ')[0]}</span>
              <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">Elite Tier</span>
            </div>
            <div className="h-10 w-10 bg-primary/10 border border-primary/20 text-primary font-bold flex items-center justify-center rounded-xl text-sm hover:bg-primary/20 transition-all shadow-sm">
              {userInitials}
            </div>
          </button>
          
          {showUserMenu && (
            <div className="absolute right-0 mt-3 w-56 bg-card border border-border rounded-2xl shadow-2xl py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200 overflow-hidden">
               <div className="px-4 py-3 border-b border-border mb-1">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-0.5">Account Details</p>
                <p className="text-sm font-bold text-foreground truncate uppercase">{userName}</p>
              </div>
              <button 
                onClick={() => { setShowUserMenu(false); navigate('/onboarding'); }}
                className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent flex items-center space-x-3 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                  <UserIcon size={16} className="text-muted-foreground" />
                </div>
                <span className="font-medium">Investor Profile</span>
              </button>
              <button 
                onClick={() => {}} 
                className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent flex items-center space-x-3 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                  <Shield size={16} className="text-muted-foreground" />
                </div>
                <span className="font-medium">Security & Keys</span>
              </button>
              <div className="h-[1px] bg-border my-1.5 mx-2"></div>
              <button 
                onClick={onLogout}
                className="w-full px-4 py-2.5 text-left text-sm text-bearish hover:bg-bearish/10 flex items-center space-x-3 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-bearish/10 flex items-center justify-center">
                  <LogOut size={16} />
                </div>
                <span className="font-bold uppercase tracking-tight">Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
