'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { Map, RefreshCw, BookOpen, Zap, TrendingUp, AlertCircle, ArrowRight, ExternalLink } from 'lucide-react';
import { generateRoadmap, type RoadmapResponse, type PaperReference } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

function PaperCard({ paper }: { paper: PaperReference }) {
  return (
    <div className="p-4 rounded-xl bg-secondary/30 border border-border hover:border-blue-500/30 transition-all">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-foreground leading-tight">{paper.title}</p>
          {paper.authors?.length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">{paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? ' et al.' : ''}{paper.year ? ` · ${paper.year}` : ''}</p>
          )}
          {paper.why_important && <p className="text-xs text-muted-foreground mt-2 italic">{paper.why_important}</p>}
        </div>
        {paper.url && (
          <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-blue-400 transition-colors flex-shrink-0 mt-0.5">
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, color, children }: { title: string; icon: any; color: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Card className="h-full">
        <div className={`flex items-center gap-2 mb-4`}>
          <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center`}>
            <Icon className="w-4 h-4 text-white" />
          </div>
          <h2 className="font-semibold text-foreground">{title}</h2>
        </div>
        {children}
      </Card>
    </motion.div>
  );
}

export default function RoadmapPage() {
  const searchParams = useSearchParams();
  const [topic, setTopic] = useState(searchParams.get('topic') || '');
  const [loading, setLoading] = useState(false);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);

  useEffect(() => {
    const t = searchParams.get('topic');
    if (t) { setTopic(t); handleGenerate(t); }
  }, []);

  const handleGenerate = async (t?: string) => {
    const q = t || topic;
    if (!q.trim()) { toast.error('Enter a research topic'); return; }
    setLoading(true);
    try {
      const data = await generateRoadmap({ topic: q });
      setRoadmap(data);
      if (data.cached) toast('Loaded from cache', { icon: '⚡' });
      else toast.success('Roadmap generated!');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to generate roadmap');
    } finally { setLoading(false); }
  };

  const topics = ['Computer Vision', 'Reinforcement Learning', 'Graph Neural Networks', 'Federated Learning', 'NLP / LLMs', 'Diffusion Models'];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Map className="w-6 h-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-foreground">Research Navigator</h1>
        </div>
        <p className="text-muted-foreground">Enter a research field and get a complete learning roadmap.</p>
      </div>

      <Card className="mb-8">
        <div className="flex gap-3">
          <input
            value={topic} onChange={e => setTopic(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleGenerate()}
            placeholder="e.g. Computer Vision, Reinforcement Learning, Graph Neural Networks..."
            className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors"
          />
          <Button onClick={() => handleGenerate()} loading={loading} icon={<Map className="w-4 h-4" />}>
            Generate
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {topics.map(t => (
            <button key={t} onClick={() => { setTopic(t); handleGenerate(t); }}
              className="text-xs px-2.5 py-1 rounded-lg glass border border-border hover:border-blue-500/40 text-muted-foreground hover:text-foreground transition-all">
              {t}
            </button>
          ))}
        </div>
      </Card>

      <AnimatePresence>
        {roadmap && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-foreground">{roadmap.topic_display}</h2>
                <div className="flex items-center gap-2 mt-1">
                  {roadmap.cached && <Badge variant="amber">Cached</Badge>}
                  <span className="text-xs text-muted-foreground font-mono">{roadmap.generated_by_model}</span>
                </div>
              </div>
              <Button variant="secondary" onClick={() => handleGenerate()} icon={<RefreshCw className="w-4 h-4" />}>Refresh</Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">

              {/* Prerequisites */}
              <Section title="Prerequisites" icon={BookOpen} color="bg-blue-500">
                <ul className="space-y-2">
                  {roadmap.prerequisites.map((p, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <ArrowRight className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
                      {p}
                    </li>
                  ))}
                </ul>
              </Section>

              {/* Learning Path */}
              <Section title="Learning Path" icon={Map} color="bg-violet-500">
                <ol className="space-y-3">
                  {roadmap.learning_path.map((step) => (
                    <li key={step.order} className="flex gap-3">
                      <span className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 text-xs flex items-center justify-center flex-shrink-0 font-mono font-bold">{step.order}</span>
                      <div>
                        <p className="text-sm font-medium text-foreground">{step.topic}</p>
                        <p className="text-xs text-muted-foreground">{step.description}</p>
                        {step.estimated_hours && <p className="text-xs text-violet-400 mt-0.5">~{step.estimated_hours}h</p>}
                      </div>
                    </li>
                  ))}
                </ol>
              </Section>

              {/* Foundational Papers */}
              <Section title="Foundational Papers" icon={BookOpen} color="bg-emerald-500">
                <div className="space-y-3">
                  {roadmap.foundational_papers.map((p, i) => <PaperCard key={i} paper={p} />)}
                </div>
              </Section>

              {/* Intermediate Papers */}
              <Section title="Intermediate Papers" icon={Zap} color="bg-amber-500">
                <div className="space-y-3">
                  {roadmap.intermediate_papers.map((p, i) => <PaperCard key={i} paper={p} />)}
                </div>
              </Section>

              {/* Advanced Papers */}
              <Section title="Advanced Papers" icon={TrendingUp} color="bg-rose-500">
                <div className="space-y-3">
                  {roadmap.advanced_papers.map((p, i) => <PaperCard key={i} paper={p} />)}
                </div>
              </Section>

              {/* Research Frontiers */}
              <Section title="Research Frontiers" icon={TrendingUp} color="bg-blue-600">
                <ul className="space-y-2">
                  {roadmap.research_frontiers.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 mt-1.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </Section>

              {/* Research Gaps */}
              <Section title="Open Problems" icon={AlertCircle} color="bg-orange-500">
                <ul className="space-y-2">
                  {roadmap.research_gaps.map((g, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <AlertCircle className="w-3.5 h-3.5 text-orange-400 flex-shrink-0 mt-0.5" />
                      {g}
                    </li>
                  ))}
                </ul>
              </Section>

              {/* Reading Order */}
              <Section title="Reading Order" icon={BookOpen} color="bg-teal-500">
                <ol className="space-y-1.5">
                  {roadmap.recommended_reading_order.map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                      <span className="text-teal-400 font-mono text-xs w-5 flex-shrink-0 mt-0.5">{i + 1}.</span>
                      {r}
                    </li>
                  ))}
                </ol>
              </Section>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
