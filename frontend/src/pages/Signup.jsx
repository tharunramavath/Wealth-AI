import React, { useState } from 'react';
import { api } from '../api/client';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Mail, Lock, Eye, EyeOff, User, Phone, Briefcase, Globe, Activity, Zap, Database, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent } from '../components/ui/Card';

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    country: 'India',
    occupation: '',
    experience_level: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const countries = ['India', 'USA', 'UK', 'UAE', 'Singapore', 'Australia', 'Canada', 'Germany'];
  const experienceLevels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];

  const validate = () => {
    const errs = {};
    if (!form.name.trim()) errs.name = 'Name is required';
    if (!form.email) errs.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Invalid email format';
    if (!form.password) errs.password = 'Password is required';
    else if (form.password.length < 6) errs.password = 'Password must be at least 6 characters';
    if (form.password !== form.confirmPassword) errs.confirmPassword = 'Passwords do not match';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    
    setLoading(true);
    try {
      const res = await api.post('/auth/signup', {
        name: form.name,
        email: form.email,
        password: form.password,
        phone: form.phone || undefined,
        country: form.country,
        occupation: form.occupation || undefined,
        experience_level: form.experience_level || undefined
      });
      
      const userId = res.data.user_id;
      const userName = form.name;
      
      api.defaults.headers.common['x-user-id'] = userId;
      localStorage.setItem('user_id', userId);
      localStorage.setItem('user_name', userName);
      
      toast.success('Account created successfully!');
      navigate('/onboarding');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Signup failed';
      toast.error(msg);
    }
    setLoading(false);
  };

  const updateField = (field, value) => {
    setForm({ ...form, [field]: value });
    if (errors[field]) setErrors({ ...errors, [field]: null });
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
            Join the Intelligence Revolution
          </div>
          <h1 className="text-6xl font-black leading-[0.9] tracking-tighter mb-8 uppercase">
            Start Your <br />
            <span className="text-white/60">Alpha Journey.</span> <br />
            Scale Your <br />
            <span className="text-white/60">Portfolio.</span>
          </h1>
          <p className="text-primary-foreground/70 text-xl font-medium leading-relaxed">
            Experience the precision of institutional-grade AI agents working for your individual wealth goals.
          </p>
        </div>

        <div className="relative z-10 space-y-4 max-w-sm">
          <SignupStep icon={CheckCircle2} label="Instant Portfolio Scoring" />
          <SignupStep icon={CheckCircle2} label="Deep-Agent Risk Analysis" />
          <SignupStep icon={CheckCircle2} label="Real-time Multi-Sector Monitoring" />
        </div>
      </div>

      {/* Form Side */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 lg:p-12 relative overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-xl animate-in fade-in slide-in-from-bottom-4 duration-700 py-10">
          <div className="lg:hidden flex items-center justify-center mb-12">
            <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
              <Activity className="text-primary-foreground" size={28} />
            </div>
            <span className="text-foreground font-black text-3xl ml-4 tracking-tighter uppercase">WealthAI</span>
          </div>

          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-4xl font-black text-foreground tracking-tight uppercase">Initialize Profile</h2>
            <p className="text-muted-foreground mt-2 font-medium">Create your credentials to access the intelligence terminal.</p>
          </div>

          <Card className="border-none shadow-2xl shadow-black/5 rounded-[2.5rem] overflow-hidden">
            <CardContent className="p-8 lg:p-10">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Identity Name *</label>
                    <div className="relative group">
                      <User className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <Input
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        placeholder="John Doe"
                        className={`pl-11 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.name ? 'ring-2 ring-destructive' : ''}`}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Email Protocol *</label>
                    <div className="relative group">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <Input
                        type="email"
                        value={form.email}
                        onChange={(e) => updateField('email', e.target.value)}
                        placeholder="investor@wealth.ai"
                        className={`pl-11 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.email ? 'ring-2 ring-destructive' : ''}`}
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Key Access *</label>
                    <div className="relative group">
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <Input
                        type={showPassword ? 'text' : 'password'}
                        value={form.password}
                        onChange={(e) => updateField('password', e.target.value)}
                        placeholder="Min 6 chars"
                        className={`pl-11 pr-12 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.password ? 'ring-2 ring-destructive' : ''}`}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Confirm Key *</label>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={form.confirmPassword}
                      onChange={(e) => updateField('confirmPassword', e.target.value)}
                      placeholder="Confirm"
                      className={`h-12 px-5 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20 ${errors.confirmPassword ? 'ring-2 ring-destructive' : ''}`}
                    />
                  </div>
                </div>
                
                <div className="flex justify-start">
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[10px] font-black text-primary hover:underline uppercase tracking-widest"
                  >
                    {showPassword ? 'Secure' : 'Reveal'} Key Visualization
                  </button>
                </div>

                <div className="h-[1px] bg-border/50 my-2"></div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Jurisdiction</label>
                    <div className="relative group">
                      <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <select
                        value={form.country}
                        onChange={(e) => updateField('country', e.target.value)}
                        className="w-full pl-11 pr-4 h-12 rounded-xl bg-accent/30 border-none focus:ring-2 focus:ring-primary/20 outline-none text-sm font-medium transition-all"
                      >
                        {countries.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Contact Protocol</label>
                    <div className="relative group">
                      <Phone className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <Input
                        type="tel"
                        value={form.phone}
                        onChange={(e) => updateField('phone', e.target.value)}
                        placeholder="+91 00000 00000"
                        className="pl-11 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Occupation</label>
                    <div className="relative group">
                      <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                      <Input
                        value={form.occupation}
                        onChange={(e) => updateField('occupation', e.target.value)}
                        placeholder="e.g., Fund Manager"
                        className="pl-11 h-12 rounded-xl bg-accent/30 border-none focus-visible:ring-primary/20"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-black text-muted-foreground uppercase tracking-widest ml-1">Expertise Tier</label>
                    <select
                      value={form.experience_level}
                      onChange={(e) => updateField('experience_level', e.target.value)}
                      className="w-full px-5 h-12 rounded-xl bg-accent/30 border-none focus:ring-2 focus:ring-primary/20 outline-none text-sm font-medium transition-all"
                    >
                      <option value="">Select Level</option>
                      {experienceLevels.map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  size="lg"
                  className="w-full h-14 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all mt-6"
                >
                  {loading ? 'Creating Identity...' : 'Confirm Registration'}
                  {!loading && <ArrowRight size={18} className="ml-3" />}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-muted-foreground mt-10 font-bold text-sm uppercase tracking-tight">
            Existing credentials found?{' '}
            <Link to="/login" className="text-primary hover:underline font-black tracking-widest">
              Resume Session
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function SignupStep({ icon: Icon, label }) {
  return (
    <div className="flex items-center space-x-3 text-white">
      <div className="p-1 rounded-full bg-white/10">
        {Icon && <Icon size={16} className="text-white" />}
      </div>
      <span className="text-sm font-bold uppercase tracking-wide opacity-90">{label}</span>
    </div>
  );
}
