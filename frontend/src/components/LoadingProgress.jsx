import React from 'react';
import { Database, BarChart3, PieChart, Brain, CheckCircle2, Loader2 } from 'lucide-react';
import clsx from 'clsx';

const STEPS = [
  { id: 1, label: 'Fetching Data', icon: Database, description: 'Loading stock history...' },
  { id: 2, label: 'Technical Analysis', icon: BarChart3, description: 'Calculating RSI, MA, volatility...' },
  { id: 3, label: 'Portfolio Impact', icon: PieChart, description: 'Analyzing sector exposure...' },
  { id: 4, label: 'AI Insights', icon: Brain, description: 'Generating personalized analysis...' },
  { id: 5, label: 'Finalizing', icon: CheckCircle2, description: 'Compiling results...' },
];

export default function LoadingProgress({ currentStep, totalSteps }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
        <h3 className="font-semibold text-gray-900">Analyzing Stock</h3>
      </div>
      
      <div className="space-y-0">
        {STEPS.map((step, index) => {
          const isCompleted = step.id < currentStep;
          const isCurrent = step.id === currentStep;
          const isPending = step.id > currentStep;
          const Icon = step.icon;
          
          return (
            <div key={step.id} className="relative">
              {index < STEPS.length - 1 && (
                <div className={clsx(
                  "absolute left-[15px] top-8 w-0.5 h-8 -translate-x-1/2",
                  isCompleted ? 'bg-green-500' : 'bg-gray-200'
                )} />
              )}
              
              <div className="flex items-start gap-4 py-2">
                <div className={clsx(
                  "relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all duration-300",
                  isCompleted && 'bg-green-500 border-green-500',
                  isCurrent && 'bg-cyan-500 border-cyan-500 animate-pulse',
                  isPending && 'bg-gray-100 border-gray-200'
                )}>
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-white" />
                  ) : isCurrent ? (
                    <Icon className="w-4 h-4 text-white" />
                  ) : (
                    <Icon className="w-4 h-4 text-gray-400" />
                  )}
                </div>
                
                <div className="flex-1 pt-1">
                  <p className={clsx(
                    "font-medium text-sm transition-colors duration-300",
                    isCompleted && 'text-green-600',
                    isCurrent && 'text-cyan-600',
                    isPending && 'text-gray-400'
                  )}>
                    {step.label}
                  </p>
                  <p className={clsx(
                    "text-xs mt-0.5 transition-opacity duration-300",
                    isCurrent ? 'text-gray-600 opacity-100' : 'opacity-60'
                  )}>
                    {isCurrent ? step.description : isCompleted ? 'Completed' : 'Pending'}
                  </p>
                </div>
                
                {isCurrent && (
                  <div className="flex items-center gap-1 pt-1">
                    <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="mt-6 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
          <span>Progress</span>
          <span>{currentStep} of {totalSteps}</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-cyan-500 to-cyan-600 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
