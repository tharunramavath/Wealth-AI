import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ShieldCheck, Target, TrendingUp, DollarSign, Edit2, Save, X } from 'lucide-react';
import { Button } from '../components/ui/Button';
import clsx from 'clsx';

export default function Onboarding() {
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState({
    risk_tolerance: '',
    investment_horizon: '',
    goals: [],
    liquidity_need: '',
    portfolio_size: ''
  });
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await api.get('/onboarding/risk-profile');
      if (res.data && res.data.risk_tolerance) {
        setProfile({
          risk_tolerance: res.data.risk_tolerance || '',
          investment_horizon: res.data.investment_horizon || '',
          goals: res.data.goals || [],
          liquidity_need: res.data.liquidity_need || '',
          portfolio_size: res.data.portfolio_size || ''
        });
      }
    } catch (e) {
      console.error('Failed to load profile:', e);
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch(step) {
      case 1: return !!profile.risk_tolerance;
      case 2: return !!profile.investment_horizon;
      case 3: return profile.goals.length > 0;
      case 4: return !!profile.liquidity_need;
      case 5: return !!profile.portfolio_size;
      default: return true;
    }
  };

  const handleNext = () => {
    if (!canProceed()) {
      setError('Please select an option to continue');
      return;
    }
    setError('');
    setStep(s => s + 1);
  };
  const handlePrev = () => {
    setError('');
    setStep(s => s - 1);
  };

  const handleSubmit = async () => {
    if (!canProceed()) {
      setError('Please fill in all fields');
      return;
    }
    try {
      await api.post('/onboarding/risk-profile', profile);
      toast.success('Profile saved successfully!');
      setIsEditing(false);
    } catch (e) {
      toast.error('Failed to save profile');
    }
  };

  const toggleGoal = (g) => {
     if (profile.goals.includes(g)) {
       setProfile({...profile, goals: profile.goals.filter(x => x !== g)});
     } else {
       setProfile({...profile, goals: [...profile.goals, g]});
     }
  };

  const isProfileComplete = () => {
    return profile.risk_tolerance && profile.investment_horizon && profile.goals.length > 0 && profile.liquidity_need && profile.portfolio_size;
  };

  if (loading) {
    return <div className="animate-pulse space-y-4"><div className="h-40 bg-terminal-card rounded-xl" /></div>;
  }

  if (!isEditing && isProfileComplete()) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Investor Profile</h1>
            <p className="text-text-muted mt-1 text-sm">Your saved preferences</p>
          </div>
          <Button 
            onClick={() => { setIsEditing(true); setStep(1); }}
            variant="bullish"
            className="flex items-center gap-2 px-4 py-2 font-medium rounded-lg transition-all text-sm shadow-sm"
          >
            <Edit2 size={16} /> Edit Profile
          </Button>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-6 rounded-xl space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-terminal-surface rounded-lg">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <ShieldCheck size={16} className="text-accent-cyan" /> Risk Tolerance
              </div>
              <p className="text-text-primary font-medium">{profile.risk_tolerance}</p>
            </div>
            <div className="p-4 bg-terminal-surface rounded-lg">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <Target size={16} className="text-accent-purple" /> Investment Horizon
              </div>
              <p className="text-text-primary font-medium">{profile.investment_horizon}</p>
            </div>
            <div className="p-4 bg-terminal-surface rounded-lg">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <TrendingUp size={16} className="text-bullish" /> Goals
              </div>
              <p className="text-text-primary font-medium">{profile.goals.join(', ')}</p>
            </div>
            <div className="p-4 bg-terminal-surface rounded-lg">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <DollarSign size={16} className="text-accent-gold" /> Liquidity Need
              </div>
              <p className="text-text-primary font-medium">{profile.liquidity_need}</p>
            </div>
          </div>
          
          <div className="p-4 bg-terminal-surface rounded-lg">
            <div className="text-text-muted text-sm mb-2">Portfolio Size</div>
            <p className="text-text-primary font-medium">{profile.portfolio_size}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8">
       <div className="flex justify-between items-center mb-6">
         <div className="text-center flex-1">
           <h1 className="text-2xl font-bold text-text-primary">{isEditing ? 'Edit Profile' : 'Investor Profile'}</h1>
           <p className="text-text-muted mt-1 text-sm">{isEditing ? 'Update your preferences' : 'Help us personalize your experience'}</p>
         </div>
         {isEditing && (
           <button onClick={() => { setIsEditing(false); loadProfile(); }} className="p-2 text-text-muted hover:text-text-primary">
             <X size={20} />
           </button>
         )}
       </div>

       <div className="bg-card/50 backdrop-blur-md border border-border/50 p-8 rounded-2xl shadow-2xl relative overflow-hidden group">
          {/* Decorative background element */}
          <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-700" />
          
          <div className="h-1.5 bg-border/30 rounded-full mb-8 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary to-accent-cyan rounded-full transition-all duration-500 shadow-[0_0_12px_theme(colors.primary/0.5)]" style={{ width: `${(step/5)*100}%` }}></div>
           </div>

           {error && (
             <div className="mb-4 p-3 bg-bearish/10 border border-bearish/30 rounded-lg text-bearish text-sm">
               {error}
             </div>
           )}

           <div className="space-y-5">
             {step === 1 && (
               <div>
                 <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <ShieldCheck className="text-accent-cyan" size={20} /> Risk Tolerance
                 </h2>
                 <div className="grid gap-3">
                   {[
                     { id: 'Conservative', desc: 'Preserve capital, minimal risk', icon: ShieldCheck },
                     { id: 'Moderate', desc: 'Balanced growth and income', icon: Target },
                     { id: 'Aggressive', desc: 'High growth, higher volatility', icon: TrendingUp }
                   ].map(r => (
                      <div key={r.id} 
                           onClick={() => setProfile({...profile, risk_tolerance: r.id})}
                           className={clsx("p-4 border rounded-xl cursor-pointer transition-all duration-300 flex justify-between items-center group/card relative overflow-hidden", 
                             profile.risk_tolerance === r.id 
                               ? "border-primary bg-primary/5 shadow-[0_0_20px_theme(colors.primary/0.1)] scale-[1.01]" 
                               : "border-border/50 bg-terminal-surface/30 hover:border-primary/50 hover:bg-primary/5"
                           )}>
                        <div className="flex items-center gap-4">
                          <div className={clsx("p-2 rounded-lg transition-colors", 
                            profile.risk_tolerance === r.id ? "bg-primary text-primary-foreground" : "bg-accent/50 text-muted-foreground group-hover/card:text-primary"
                          )}>
                            <r.icon size={20} />
                          </div>
                          <div>
                            <h4 className="font-bold text-foreground text-base tracking-tight">{r.id}</h4>
                            <p className="text-xs text-muted-foreground font-medium uppercase tracking-tight">{r.desc}</p>
                          </div>
                        </div>
                        <div className={clsx("w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all", 
                          profile.risk_tolerance === r.id ? "border-primary bg-primary" : "border-border/50 bg-background"
                        )}>
                          {profile.risk_tolerance === r.id && <div className="w-2 h-2 bg-primary-foreground rounded-full shadow-[0_0_8px_rgba(255,255,255,0.8)]" />}
                        </div>
                     </div>
                   ))}
                 </div>
               </div>
             )}

             {step === 2 && (
               <div>
                 <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <Target className="text-accent-purple" size={20} /> Investment Horizon
                 </h2>
                 <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {['Short term (0-3 yrs)', 'Medium term (3-7 yrs)', 'Long term (7+ yrs)'].map(h => (
                      <div key={h} 
                           onClick={() => setProfile({...profile, investment_horizon: h})}
                           className={clsx("p-4 text-center border rounded-xl cursor-pointer transition-all duration-300 font-bold text-sm", 
                             profile.investment_horizon === h 
                               ? "border-primary bg-primary/5 text-primary shadow-[0_0_15px_theme(colors.primary/0.1)] scale-[1.02]" 
                               : "border-border/50 text-muted-foreground bg-terminal-surface/30 hover:border-primary/50 hover:bg-primary/5 hover:text-foreground"
                           )}>
                        <div className="uppercase tracking-widest text-[10px] mb-1 opacity-60">Horizon</div>
                        {h.split('(')[0].trim()}
                        <div className="text-[10px] block mt-1 opacity-50 font-medium italic">{h.match(/\(([^)]+)\)/)?.[0] || ""}</div>
                      </div>
                    ))}
                 </div>
               </div>
             )}

             {step === 3 && (
               <div>
                 <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <TrendingUp className="text-bullish" size={20} /> Goals
                 </h2>
                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {['Wealth growth', 'Passive income', 'Retirement', 'Capital preservation'].map(g => (
                      <div key={g} 
                           onClick={() => toggleGoal(g)}
                           className={clsx("p-4 border rounded-xl cursor-pointer transition-all duration-300 flex items-center justify-between group/goal", 
                             profile.goals.includes(g) 
                               ? "border-primary bg-primary/5 shadow-[0_0_15px_theme(colors.primary/0.1)]" 
                               : "border-border/50 bg-terminal-surface/30 hover:border-primary/50 hover:bg-primary/5"
                           )}>
                        <span className={clsx("text-sm font-bold tracking-tight transition-colors", 
                          profile.goals.includes(g) ? "text-primary" : "text-foreground group-hover/goal:text-primary"
                        )}>{g}</span>
                        <div className={clsx("w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all duration-300 transform", 
                            profile.goals.includes(g) ? "bg-primary border-primary scale-110 shadow-lg shadow-primary/20" : "border-border/50 bg-background"
                        )}>
                            {profile.goals.includes(g) && <span className="text-slate-950 dark:text-slate-50 text-xs font-black">✓</span>}
                        </div>
                     </div>
                    ))}
                 </div>
               </div>
             )}

             {step === 4 && (
               <div>
                 <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <DollarSign className="text-accent-gold" size={20} /> Liquidity
                 </h2>
                 <div className="grid grid-cols-3 gap-3">
                    {['Low', 'Medium', 'High'].map(l => (
                      <div key={l} 
                           onClick={() => setProfile({...profile, liquidity_need: l})}
                           className={clsx("p-4 text-center border rounded-xl cursor-pointer transition-all duration-300 font-bold", 
                             profile.liquidity_need === l 
                               ? "border-primary bg-primary/5 text-primary shadow-[0_0_15px_theme(colors.primary/0.1)] scale-[1.02]" 
                               : "border-border/50 text-muted-foreground bg-terminal-surface/30 hover:border-primary/50 hover:bg-primary/5 hover:text-foreground"
                           )}>
                        <div className="text-[10px] uppercase tracking-widest mb-1 opacity-50 font-medium">Requirement</div>
                        {l}
                      </div>
                    ))}
                 </div>
               </div>
             )}

             {step === 5 && (
               <div>
                 <h2 className="text-lg font-semibold text-text-primary mb-4">Portfolio Size</h2>
                 <div className="grid grid-cols-2 gap-3">
                    {['< $10k', '$10k-$100k', '$100k-$1M', '$1M+'].map(ps => (
                      <div key={ps} 
                           onClick={() => setProfile({...profile, portfolio_size: ps})}
                           className={clsx("p-4 text-center border rounded-xl cursor-pointer transition-all duration-300 font-black", 
                             profile.portfolio_size === ps 
                               ? "border-primary bg-primary/5 text-primary shadow-[0_0_15px_theme(colors.primary/0.1)] scale-[1.05]" 
                               : "border-border/50 text-muted-foreground bg-terminal-surface/30 hover:border-primary/50 hover:bg-primary/5 hover:text-foreground"
                           )}>
                        <div className="text-[10px] uppercase tracking-widest mb-1 opacity-50 font-medium">Assets Under Management</div>
                        {ps}
                      </div>
                    ))}
                 </div>
               </div>
             )}
         </div>

          <div className="mt-10 pt-6 border-t border-border/50 flex justify-between items-center relative z-10">
             <Button onClick={handlePrev} disabled={step === 1} variant="outline" className="px-8 rounded-xl text-xs font-bold uppercase tracking-widest h-11">
                Back
             </Button>
             {step < 5 ? (
                <Button onClick={handleNext} 
                  variant="bullish"
                  disabled={(step === 1 && !profile.risk_tolerance) || (step === 2 && !profile.investment_horizon) || (step === 3 && profile.goals.length === 0) || (step === 4 && !profile.liquidity_need)}
                  className="px-10 font-black rounded-xl transition-all duration-300 h-11 shadow-lg shadow-bullish/20 hover:shadow-bullish/40 active:scale-95 uppercase tracking-wider text-xs">
                  Continue Phase {step}
                </Button>
             ) : (
                <Button onClick={handleSubmit} disabled={!profile.portfolio_size} 
                  variant="bullish"
                  className="px-10 font-black rounded-xl transition-all duration-300 h-11 flex items-center gap-2 shadow-lg shadow-bullish/20 hover:shadow-bullish/40 active:scale-95 uppercase tracking-wider text-xs">
                  <Save size={16} className="animate-pulse" /> Complete Blueprint
                </Button>
             )}
          </div>
      </div>
    </div>
  );
}
