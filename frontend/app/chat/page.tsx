'use client';
import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { MessageSquare, Send, BookOpen, ChevronDown, ChevronUp, Upload } from 'lucide-react';
import { chatWithPaper, type ChatResponse, type Citation } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import Link from 'next/link';

interface Message { role: 'user' | 'assistant'; content: string; citations?: Citation[]; }

function CitationBlock({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  if (!citations.length) return null;
  return (
    <div className="mt-3 border-t border-border pt-3">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
        <BookOpen className="w-3.5 h-3.5" />
        {citations.length} source{citations.length > 1 ? 's' : ''}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="mt-2 space-y-2">
              {citations.map((c, i) => (
                <div key={i} className="p-3 rounded-lg bg-secondary/30 border border-border">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="blue">Ref {c.chunk_index + 1}</Badge>
                    {c.page && <span className="text-xs text-muted-foreground">Page {c.page}</span>}
                    <span className="text-xs text-emerald-400 ml-auto">{Math.round(c.relevance_score * 100)}% match</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed italic">"{c.text_snippet}"</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const STARTERS = [
  'What are the key contributions of this paper?',
  'Explain the methodology in simple terms',
  'What limitations does the paper mention?',
  'What datasets were used for evaluation?',
  'How does this compare to prior work?',
];

export default function ChatPage() {
  const searchParams = useSearchParams();
  const [paperId, setPaperId] = useState(searchParams.get('paper_id') || '');
  const [inputId, setInputId] = useState(searchParams.get('paper_id') || '');
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async (q?: string) => {
    const text = q || question;
    if (!text.trim()) return;
    if (!paperId.trim()) { toast.error('Enter a Paper ID first'); return; }

    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setQuestion('');
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const data = await chatWithPaper(paperId, text, history);
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, citations: data.citations }]);
    } catch (e: any) {
      const err = e?.response?.data?.detail || 'Chat failed';
      toast.error(err);
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err}` }]);
    } finally { setLoading(false); }
  };

  const started = paperId && messages.length > 0;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6 flex-shrink-0">
        <h1 className="text-2xl font-bold text-foreground mb-1">Paper Chat</h1>
        <p className="text-muted-foreground">Ask questions about an uploaded paper and get cited answers.</p>
      </div>

      {/* Paper ID input */}
      <Card className="mb-4 flex-shrink-0">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1.5 block">Paper ID (from Upload page)</label>
            <input value={inputId} onChange={e => setInputId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors font-mono" />
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setPaperId(inputId); setMessages([]); }} icon={<MessageSquare className="w-4 h-4" />}>
              Load Paper
            </Button>
            <Link href="/upload">
              <Button variant="ghost" icon={<Upload className="w-4 h-4" />}>Upload</Button>
            </Link>
          </div>
        </div>
      </Card>

      {/* Chat area */}
      {paperId ? (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto space-y-4 pb-4">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <MessageSquare className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground text-sm mb-6">Ask anything about your paper</p>
                <div className="flex flex-col gap-2 max-w-sm mx-auto">
                  {STARTERS.map(s => (
                    <button key={s} onClick={() => send(s)}
                      className="text-left text-xs p-3 glass border border-border rounded-xl text-muted-foreground hover:text-foreground hover:border-blue-500/30 transition-all">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <AnimatePresence>
              {messages.map((msg, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white rounded-br-sm'
                      : 'glass border border-border text-foreground rounded-bl-sm'
                  }`}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.citations && <CitationBlock citations={msg.citations} />}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {loading && (
              <div className="flex justify-start">
                <div className="glass border border-border rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
                  <Spinner size="sm" />
                  <span className="text-xs text-muted-foreground">Searching paper...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex-shrink-0 pt-4 border-t border-border">
            <div className="flex gap-3">
              <input value={question} onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
                placeholder="Ask about this paper... (Enter to send)"
                className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
              <Button onClick={() => send()} loading={loading} disabled={!question.trim()} icon={<Send className="w-4 h-4" />}>
                Send
              </Button>
            </div>
            {messages.length > 0 && (
              <button onClick={() => setMessages([])} className="text-xs text-muted-foreground hover:text-foreground mt-2 transition-colors">
                Clear conversation
              </button>
            )}
          </div>
        </div>
      ) : (
        <Card className="text-center py-16 flex-1">
          <MessageSquare className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground mb-4">Enter a Paper ID above to start chatting</p>
          <Link href="/upload">
            <Button variant="secondary" icon={<Upload className="w-4 h-4" />}>Upload a PDF first</Button>
          </Link>
        </Card>
      )}
    </div>
  );
}
