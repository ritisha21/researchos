'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, BookOpen, Map, Upload, MessageSquare, Sparkles, Search } from 'lucide-react';

const features = [
  {
    icon: Map,
    title: 'Research Navigator',
    description: 'Enter any topic and get a full learning roadmap — prerequisites, foundational to advanced papers, research frontiers, and open problems.',
    href: '/roadmap',
    color: 'from-blue-500/20 to-blue-600/5',
    border: 'border-blue-500/20',
    iconColor: 'text-blue-400',
  },
  {
    icon: Search,
    title: 'Paper Search',
    description: 'Search across Semantic Scholar and arXiv simultaneously. Get deduplicated, citation-sorted results from millions of papers.',
    href: '/papers',
    color: 'from-violet-500/20 to-violet-600/5',
    border: 'border-violet-500/20',
    iconColor: 'text-violet-400',
  },
  {
    icon: BookOpen,
    title: 'Paper Analysis',
    description: 'Summarise any paper, get beginner-friendly explanations, generate study notes, key takeaways, and multi-paper literature reviews.',
    href: '/papers',
    color: 'from-emerald-500/20 to-emerald-600/5',
    border: 'border-emerald-500/20',
    iconColor: 'text-emerald-400',
  },
  {
    icon: Upload,
    title: 'PDF Upload',
    description: 'Upload your own research PDFs. The system extracts, chunks, and embeds them into a vector database for intelligent retrieval.',
    href: '/upload',
    color: 'from-amber-500/20 to-amber-600/5',
    border: 'border-amber-500/20',
    iconColor: 'text-amber-400',
  },
  {
    icon: MessageSquare,
    title: 'Paper Chat',
    description: 'Ask questions about uploaded papers and get cited answers grounded in the actual text. Multi-turn conversations supported.',
    href: '/chat',
    color: 'from-rose-500/20 to-rose-600/5',
    border: 'border-rose-500/20',
    iconColor: 'text-rose-400',
  },
];

const examples = [
  { topic: 'Computer Vision', papers: ['ResNet', 'ViT', 'CLIP'] },
  { topic: 'Reinforcement Learning', papers: ['DQN', 'PPO', 'AlphaGo'] },
  { topic: 'Graph Neural Networks', papers: ['GCN', 'GAT', 'GraphSAGE'] },
  { topic: 'Federated Learning', papers: ['FedAvg', 'FedProx', 'SCAFFOLD'] },
];

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      {/* Hero */}
      <section className="relative px-6 pt-24 pb-20 text-center max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs text-muted-foreground mb-8 border border-border">
            <Sparkles className="w-3 h-3 text-blue-400" />
            Powered by Gemini · Semantic Scholar · arXiv
          </div>

          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight mb-6">
            <span className="gradient-text">Research,</span>
            <br />
            <span className="text-foreground">accelerated.</span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            ResearchOS is an AI-powered platform that helps you navigate research fields,
            understand papers instantly, and build deep knowledge — from beginner to frontier.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/roadmap"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-500 hover:bg-blue-400 text-white font-medium transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/25"
            >
              Generate a Roadmap
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/papers"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl glass border border-border hover:border-blue-500/40 text-foreground font-medium transition-all duration-200"
            >
              Search Papers
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Feature Cards */}
      <section className="px-6 pb-20 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
            >
              <Link
                href={feature.href}
                className={`block p-6 rounded-2xl bg-gradient-to-br ${feature.color} border ${feature.border} hover:scale-[1.02] transition-all duration-200 h-full`}
              >
                <feature.icon className={`w-6 h-6 ${feature.iconColor} mb-4`} />
                <h3 className="font-semibold text-foreground mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Example topics */}
      <section className="px-6 pb-24 max-w-4xl mx-auto text-center">
        <p className="section-label mb-6">Example topics</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {examples.map((ex) => (
            <Link
              key={ex.topic}
              href={`/roadmap?topic=${encodeURIComponent(ex.topic)}`}
              className="glass border border-border rounded-xl p-4 hover:border-blue-500/40 transition-all duration-200 text-left"
            >
              <p className="font-medium text-sm text-foreground mb-2">{ex.topic}</p>
              <div className="flex flex-wrap gap-1">
                {ex.papers.map((p) => (
                  <span key={p} className="text-xs px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">
                    {p}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
