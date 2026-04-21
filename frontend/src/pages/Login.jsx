import React, { useState } from 'react';
import { api } from '../api/client';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Mail, Lock, Eye, EyeOff, TrendingUp, Activity, Zap, Database, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent } from '../components/ui/Card';

export default function Login({ onLoginSuccess }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const validate = () => {
    const errs = {};
    if (!form.email) errs.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Invalid email format';
    if (!form.password) errs.password = 'Password is required';
    else if (form.password.length < 6) errs.password = 'Password must be at least 6 characters';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    
    setLoading(true);
    try {
      const res = await api.post('/auth/login', form);
      const userId = res.data.user_id;
      const userName = res.data.name || 'Investor';
      
      api.defaults.headers.common['x-user-id'] = userId;
      localStorage.setItem('user_id', userId);
      localStorage.setItem('user_name', userName);
      localStorage.setItem('show_welcome', 'true');
      
      let hasProfile = false;
      try {
        const profile = await api.get('/onboarding/risk-profile');
        hasProfile = !!profile.data?.risk_tolerance;
      } catch {
        hasProfile = false;
      }
      
      if (onLoginSuccess) onLoginSuccess();
      navigate(hasProfile ? '/' : '/onboarding');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Please check your credentials.';
      toast.error(msg);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col lg:flex-row overflow-hidden">
      {/* Brand Side */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary p-16 flex-col justify-between relative overflow-hidden text-primary-foreground">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-white/5 rounded-full -mr-96 -mt-96 blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-black/10 rounded-full -ml-48 -mb-48 blur-3xl"></div>
        
        <div className="relative z-10 flex items-center space-x-3 group cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-12 h-12 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-500">
            <Activity className="text-white" size={28} />
          </div>
          <span className="font-black text-3xl tracking-tighter uppercase">WealthAI</span>
        </div>

        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-[10px] font-black uppercase tracking-widest mb-6 animate-pulse">
            <Sparkles size={12} className="mr-2" />
            Next-Gen Financial Intelligence
          </div>
          <h1 className="text-6xl font-black leading-[0.9] tracking-tighter mb-8 uppercase">
            Institutional <br />
            <span className="text-white/60">Precision.</span> <br />
            Personal <br />
            <span className="text-white/60">Execution.</span>
          </h1>
          <p className="text-primary-foreground/70 text-xl font-medium leading-relaxed">
            Harness the power of multi-agent LLM reasoning and real-time market signals to optimize your portfolio.
          </p>
        </div>

        <div className="relative z-10 grid grid-cols-2 gap-6 mt-12">
          <AuthFeature icon={Zap} label="Real-time Signals" sub="NSE/BSE Pipeline" />
          <AuthFeature icon={Database} label="AI Insights" sub="Deep-Agent Reasoning" />
        </div>
      </div>

      {/* Form Side */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 lg:p-16 relative">
        <div className="w-full max-w-md animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="lg:hidden flex items-center justify-center mb-12">
            <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
              <Activity className="text-primary-foreground" size={28} />
            </div>
            <span className="text-foreground font-black text-3xl ml-4 tracking-tighter uppercase">WealthAI</span>
          </div>

          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-4xl font-black text-foreground tracking-tight uppercase">Access Terminal</h2>
            <p className="text-muted-foreground mt-2 font-medium">Authenticate to resume portfolio intelligence.</p>
          </div>

          <Card className="border-none shadow-2xl shadow-black/5 rounded-[2rem] overflow-hidden">
            <CardContent className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Email Protocol</label>
                  <div className="relative group">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <Input
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      placeholder="investor@intelligence.ai"
                      className={`pl-11 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.email ? 'ring-2 ring-destructive' : ''}`}
                    />
                  </div>
                  {errors.email && <p className="text-destructive text-[10px] font-bold uppercase tracking-tight mt-1 ml-1">{errors.email}</p>}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between ml-1">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest">Key Access</label>
                    <button type="button" className="text-[10px] font-bold text-primary hover:underline uppercase tracking-tighter">Identity Recovery?</button>
                  </div>
                  <div className="relative group">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="••••••••"
                      className={`pl-11 pr-12 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.password ? 'ring-2 ring-destructive' : ''}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {errors.password && <p className="text-destructive text-[10px] font-bold uppercase tracking-tight mt-1 ml-1">{errors.password}</p>}
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  size="lg"
                  className="w-full h-14 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all mt-4"
                >
                  {loading ? (
                    <div className="flex items-center">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-3"></div>
                      Authenticating...
                    </div>
                  ) : (
                    <div className="flex items-center">
                      Initialize Session
                      <ArrowRight size={18} className="ml-3 group-hover:translate-x-1 transition-transform" />
                    </div>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-muted-foreground mt-10 font-bold text-sm uppercase tracking-tight">
            New Signal detected?{' '}
            <Link to="/signup" className="text-primary hover:underline font-black tracking-widest">
              Create ID
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function AuthFeature({ icon: Icon, label, sub }) {
  return (
    <div className="flex items-center space-x-4 p-4 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all cursor-default">
      <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0 shadow-inner">
        {Icon && <Icon size={20} className="text-white" />}
      </div>
      <div>
        <p className="text-sm font-black uppercase tracking-tighter leading-tight">{label}</p>
        <p className="text-[10px] text-white/50 font-bold uppercase tracking-widest">{sub}</p>
      </div>
    </div>
  );
}
