import React, { useEffect, useState } from 'react';
import { SignalCard } from './components/SignalCard';

export default function App() {
  const [signals, setSignals] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/signals');

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setSignals((prev) => [data, ...prev]);
    };

    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans" dir="rtl">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h1 className="text-xl font-bold text-slate-100">شاشة الأحداث وإشارات الذكاء الاصطناعي (AI Live Feed)</h1>
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
          <span className="text-sm text-slate-400">{connected ? 'متصل بـ API Gateway' : 'غير متصل'}</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
        {signals.length === 0 ? (
          <p className="col-span-2 text-center text-slate-500 py-12">في انتظار بث الإشارات اللحظية...</p>
        ) : (
          signals.map((sig, idx) => <SignalCard key={sig.signal_id || idx} signal={sig} />)
        )}
      </main>
    </div>
  );
}
