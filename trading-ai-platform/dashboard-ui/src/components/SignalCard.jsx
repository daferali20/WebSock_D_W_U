import React from 'react';

export const SignalCard = ({ signal }) => {
  if (!signal) return null;
  const isBuy = signal.action === 'BUY';

  return (
    <div className={`p-6 rounded-xl border-2 shadow-xl bg-slate-900 text-white ${isBuy ? 'border-emerald-500' : 'border-rose-500'}`}>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-bold">{signal.symbol}</h2>
          <span className="text-xs text-slate-400">{signal.timestamp}</span>
        </div>
        <span className={`px-4 py-1.5 rounded-full font-black text-sm ${isBuy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500' : 'bg-rose-500/20 text-rose-400 border border-rose-500'}`}>
          {signal.action} ({Math.round(signal.confidence * 100)}%)
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 py-3 bg-slate-800/50 rounded-lg text-center mb-4 text-sm">
        <div>
          <p className="text-slate-400 text-xs">السعر الحالي</p>
          <p className="font-semibold text-slate-200">${signal.current_price}</p>
        </div>
        <div>
          <p className="text-slate-400 text-xs">الهدف</p>
          <p className="font-semibold text-emerald-400">${signal.target_price}</p>
        </div>
        <div>
          <p className="text-slate-400 text-xs">وقف الخسارة</p>
          <p className="font-semibold text-rose-400">${signal.stop_loss}</p>
        </div>
      </div>

      <div className="space-y-1 mb-5">
        <p className="text-xs font-semibold text-slate-400">أسباب التوصية:</p>
        {signal.reasons?.map((reason, idx) => (
          <p key={idx} className="text-xs text-slate-300 flex items-center gap-1">
            • {reason}
          </p>
        ))}
      </div>

      <div className="flex gap-3">
        <button className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 font-bold rounded-lg text-sm transition">
          تنفيذ يدوياً
        </button>
        <button className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-lg text-sm transition">
          تجاهل
        </button>
      </div>
    </div>
  );
};
