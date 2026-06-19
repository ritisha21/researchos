'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { Search, BookOpen, FileText, Lightbulb, Star, Library, ExternalLink, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { searchPapers, summarisePaper, explainPaper, getNotes, getTakeaways, getLiteratureReview, type PaperSearchResult, type SummariseResponse, type ExplainResponse, type NotesResponse, type TakeawaysResponse, type LiteratureReviewResponse } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';

type Tab = 'search' | 'analyse' | 'review';
type AnalyseMode = 'summarise' | 'explain' | 'notes' | 'takeaways';

function PaperResultCard({ paper, onAnalyse }: { paper: PaperSearchResult; onAnalyse: (p: PaperSearchResult) => void }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="p-5 rounded-xl glass border border-border hover:border-blue-500/20 transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <Badge variant={paper.source === 'semantic_scholar' ? 'blue' : 'violet'}>{paper.source === 'semantic_scholar' ? 'S2' : 'arXiv'}</Badge>
            {paper.year && <span className="text-xs text-muted-foreground">{paper.year}</span>}
            {paper.citation_count > 0 && <span className="text-xs text-amber-400">⭐ {paper.citation_count.toLocaleString()} citations</span>}
          </div>
          <h3 className="font-medium text-foreground text-sm leading-snug">{paper.title}</h3>
          {paper.authors?.length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">{paper.authors.slice(0, 4).join(', ')}{paper.authors.length > 4 ? ' et al.' : ''}</p>
          )}
          {paper.abstract && (
            <div className="mt-2">
              <p className={`text-xs text-muted-foreground leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>{paper.abstract}</p>
              {paper.abstract.length > 150 && (
                <button onClick={() => setExpanded(!expanded)} className="text-xs text-blue-400 mt-1 flex items-center gap-1">
                  {expanded ? <><ChevronUp className="w-3 h-3" />Less</> : <><ChevronDown className="w-3 h-3" />More</>}
                </button>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 flex-shrink-0">
          {paper.url && <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-blue-400 transition-colors"><ExternalLink className="w-4 h-4" /></a>}
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border">
        <Button variant="secondary" onClick={() => onAnalyse(paper)} icon={<BookOpen className="w-3.5 h-3.5" />} className="text-xs py-1.5">
          Analyse Paper
        </Button>
      </div>
    </div>
  );
}

export default function PapersPage() {
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('relevance');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<PaperSearchResult[]>([]);

  const [analyseTitle, setAnalyseTitle] = useState('');
  const [analyseAbstract, setAnalyseAbstract] = useState('');
  const [analyseMode, setAnalyseMode] = useState<AnalyseMode>('summarise');
  const [analysing, setAnalysing] = useState(false);
  const [summary, setSummary] = useState<SummariseResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [notes, setNotes] = useState<NotesResponse | null>(null);
  const [takeaways, setTakeaways] = useState<TakeawaysResponse | null>(null);

  const [reviewTitles, setReviewTitles] = useState('');
  const [reviewFocus, setReviewFocus] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [review, setReview] = useState<LiteratureReviewResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) { toast.error('Enter a search query'); return; }
    setSearching(true); setResults([]);
    try {
      const data = await searchPapers(query, 10, sortBy);
      setResults(data.results);
      toast.success(`${data.total_results} papers found`);
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Search failed'); }
    finally { setSearching(false); }
  };

  const handleAnalyse = async () => {
    if (!analyseTitle.trim()) { toast.error('Enter a paper title'); return; }
    setAnalysing(true); setSummary(null); setExplanation(null); setNotes(null); setTakeaways(null);
    try {
      if (analyseMode === 'summarise') { const d = await summarisePaper(analyseTitle, analyseAbstract || undefined); setSummary(d); }
      else if (analyseMode === 'explain') { const d = await explainPaper(analyseTitle, analyseAbstract || undefined); setExplanation(d); }
      else if (analyseMode === 'notes') { const d = await getNotes(analyseTitle, analyseAbstract || undefined); setNotes(d); }
      else { const d = await getTakeaways(analyseTitle, analyseAbstract || undefined); setTakeaways(d); }
      toast.success('Analysis complete!');
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Analysis failed'); }
    finally { setAnalysing(false); }
  };

  const handleReview = async () => {
    const titles = reviewTitles.split('\n').map(t => t.trim()).filter(Boolean);
    if (titles.length < 1) { toast.error('Enter at least one paper title'); return; }
    setReviewing(true); setReview(null);
    try {
      const d = await getLiteratureReview(titles, undefined, reviewFocus || undefined);
      setReview(d); toast.success('Literature review generated!');
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Review failed'); }
    finally { setReviewing(false); }
  };

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'search', label: 'Search Papers', icon: Search },
    { id: 'analyse', label: 'Analyse Paper', icon: BookOpen },
    { id: 'review', label: 'Literature Review', icon: Library },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-1">Research Assistant</h1>
        <p className="text-muted-foreground">Search papers, get AI-powered analysis, and generate literature reviews.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 glass rounded-xl border border-border mb-8 w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === id ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {/* Search Tab */}
      {activeTab === 'search' && (
        <div className="space-y-6">
          <Card>
            <div className="flex gap-3">
              <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Search papers... e.g. 'deep residual learning', 'attention mechanism'"
                className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
              <select value={sortBy} onChange={e => setSortBy(e.target.value)}
                className="bg-secondary/50 border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none">
                <option value="relevance">Relevance</option>
                <option value="citation_count">Citations</option>
                <option value="year">Year</option>
              </select>
              <Button onClick={handleSearch} loading={searching} icon={<Search className="w-4 h-4" />}>Search</Button>
            </div>
          </Card>
          {searching && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}
          {results.length > 0 && (
            <div className="space-y-3">
              {results.map((r, i) => (
                <motion.div key={r.external_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
                  <PaperResultCard paper={r} onAnalyse={p => { setAnalyseTitle(p.title); setAnalyseAbstract(p.abstract || ''); setActiveTab('analyse'); }} />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analyse Tab */}
      {activeTab === 'analyse' && (
        <div className="space-y-6">
          <Card>
            <div className="space-y-3">
              <input value={analyseTitle} onChange={e => setAnalyseTitle(e.target.value)}
                placeholder="Paper title e.g. 'Attention Is All You Need'"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
              <textarea value={analyseAbstract} onChange={e => setAnalyseAbstract(e.target.value)} rows={3}
                placeholder="Abstract (optional — improves accuracy)"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors resize-none" />
              <div className="flex flex-wrap gap-2">
                {(['summarise', 'explain', 'notes', 'takeaways'] as AnalyseMode[]).map(m => (
                  <button key={m} onClick={() => setAnalyseMode(m)}
                    className={`px-3 py-1.5 rounded-lg text-sm capitalize transition-all ${analyseMode === m ? 'bg-blue-500 text-white' : 'glass border border-border text-muted-foreground hover:text-foreground'}`}>
                    {m}
                  </button>
                ))}
              </div>
              <Button onClick={handleAnalyse} loading={analysing} icon={<BookOpen className="w-4 h-4" />}>Analyse</Button>
            </div>
          </Card>

          {analysing && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}

          <AnimatePresence>
            {summary && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <Card>
                  <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2"><FileText className="w-4 h-4 text-blue-400" />Summary</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{summary.summary}</p>
                </Card>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { title: 'Key Contributions', items: summary.key_contributions, color: 'text-emerald-400', icon: Star },
                    { title: 'Limitations', items: summary.limitations, color: 'text-rose-400', icon: AlertCircle },
                    { title: 'Future Work', items: summary.future_work, color: 'text-violet-400', icon: Lightbulb },
                  ].map(({ title, items, color, icon: Icon }) => (
                    <Card key={title}>
                      <h3 className={`font-semibold text-sm mb-3 flex items-center gap-2 ${color}`}><Icon className="w-4 h-4" />{title}</h3>
                      <ul className="space-y-2">{items.map((item, i) => <li key={i} className="text-xs text-muted-foreground flex gap-2"><span className="flex-shrink-0 mt-0.5">•</span>{item}</li>)}</ul>
                    </Card>
                  ))}
                </div>
              </motion.div>
            )}
            {explanation && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <Card><h3 className="font-semibold text-foreground mb-3 flex items-center gap-2"><Lightbulb className="w-4 h-4 text-amber-400" />Beginner Explanation</h3>
                  <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">{explanation.explanation}</div></Card>
              </motion.div>
            )}
            {notes && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <Card><h3 className="font-semibold text-foreground mb-4 flex items-center gap-2"><FileText className="w-4 h-4 text-blue-400" />Study Notes</h3>
                  <ul className="space-y-2">{notes.notes.map((n, i) => <li key={i} className="flex gap-3 text-sm text-muted-foreground"><span className="text-blue-400 font-mono text-xs mt-0.5 flex-shrink-0">{String(i+1).padStart(2,'0')}</span>{n}</li>)}</ul></Card>
              </motion.div>
            )}
            {takeaways && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <Card><h3 className="font-semibold text-foreground mb-4 flex items-center gap-2"><Star className="w-4 h-4 text-amber-400" />Key Takeaways</h3>
                  <ul className="space-y-3">{takeaways.takeaways.map((t, i) => <li key={i} className="flex gap-3 p-3 rounded-lg bg-secondary/30 text-sm text-muted-foreground"><span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center flex-shrink-0 font-bold">{i+1}</span>{t}</li>)}</ul></Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Literature Review Tab */}
      {activeTab === 'review' && (
        <div className="space-y-6">
          <Card>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Paper titles (one per line)</label>
                <textarea value={reviewTitles} onChange={e => setReviewTitles(e.target.value)} rows={6}
                  placeholder={"Attention Is All You Need\nBERT: Pre-training of Deep Bidirectional Transformers\nGPT-3: Language Models are Few-Shot Learners"}
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors resize-none font-mono" />
              </div>
              <input value={reviewFocus} onChange={e => setReviewFocus(e.target.value)}
                placeholder="Focus (optional) e.g. 'compare pre-training strategies'"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
              <Button onClick={handleReview} loading={reviewing} icon={<Library className="w-4 h-4" />}>Generate Literature Review</Button>
            </div>
          </Card>

          {reviewing && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}

          {review && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              <Card>
                <h3 className="font-semibold text-foreground mb-3">Literature Review <Badge variant="blue">{review.papers_reviewed} papers</Badge></h3>
                <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">{review.review}</div>
              </Card>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card><h3 className="font-semibold text-sm text-emerald-400 mb-3">Common Themes</h3><ul className="space-y-1.5">{review.themes.map((t,i) => <li key={i} className="text-xs text-muted-foreground flex gap-2"><span className="text-emerald-400 flex-shrink-0">•</span>{t}</li>)}</ul></Card>
                <Card><h3 className="font-semibold text-sm text-rose-400 mb-3">Research Gaps</h3><ul className="space-y-1.5">{review.gaps.map((g,i) => <li key={i} className="text-xs text-muted-foreground flex gap-2"><span className="text-rose-400 flex-shrink-0">•</span>{g}</li>)}</ul></Card>
                <Card><h3 className="font-semibold text-sm text-violet-400 mb-3">Reading Order</h3><ol className="space-y-1.5">{review.recommended_reading_order.map((r,i) => <li key={i} className="text-xs text-muted-foreground flex gap-2"><span className="text-violet-400 font-mono flex-shrink-0">{i+1}.</span>{r}</li>)}</ol></Card>
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}

function AlertCircle({ className }: { className?: string }) {
  return <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>;
}
