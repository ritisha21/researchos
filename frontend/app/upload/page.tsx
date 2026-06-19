'use client';
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { Upload, FileText, CheckCircle, Copy, MessageSquare } from 'lucide-react';
import { uploadPdf, type UploadResponse } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import Link from 'next/link';

export default function UploadPage() {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [authors, setAuthors] = useState('');
  const [year, setYear] = useState('');
  const [abstract, setAbstract] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === 'application/pdf') { setFile(f); if (!title) setTitle(f.name.replace('.pdf', '')); }
    else toast.error('Only PDF files are accepted');
  }, [title]);

  const handleUpload = async () => {
    if (!file) { toast.error('Select a PDF file'); return; }
    if (!title.trim()) { toast.error('Enter a paper title'); return; }
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title);
      form.append('authors', authors);
      if (year) form.append('year', year);
      if (abstract) form.append('abstract', abstract);
      const data = await uploadPdf(form);
      setResult(data);
      toast.success(`Indexed ${data.chunks_indexed} chunks!`);
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Upload failed'); }
    finally { setUploading(false); }
  };

  const copyId = () => { if (result) { navigator.clipboard.writeText(result.paper_id); toast.success('Copied!'); } };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-1">Upload PDF</h1>
        <p className="text-muted-foreground">Upload a research paper PDF to index it for AI-powered chat.</p>
      </div>

      {!result ? (
        <div className="space-y-4">
          {/* Drop zone */}
          <div onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)} onDrop={onDrop}
            className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${dragging ? 'border-blue-500 bg-blue-500/5' : 'border-border hover:border-blue-500/40'}`}
            onClick={() => document.getElementById('file-input')?.click()}>
            <input id="file-input" type="file" accept=".pdf" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) { setFile(f); if (!title) setTitle(f.name.replace('.pdf', '')); } }} />
            <Upload className={`w-10 h-10 mx-auto mb-3 ${dragging ? 'text-blue-400' : 'text-muted-foreground'}`} />
            {file ? (
              <div>
                <p className="font-medium text-foreground">{file.name}</p>
                <p className="text-sm text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <Badge variant="emerald" className="mt-2">PDF ready</Badge>
              </div>
            ) : (
              <div>
                <p className="font-medium text-foreground">Drop your PDF here</p>
                <p className="text-sm text-muted-foreground mt-1">or click to browse · Max 50MB</p>
              </div>
            )}
          </div>

          {/* Metadata */}
          <Card>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Paper Title *</label>
                <input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Deep Residual Learning for Image Recognition"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Authors (comma-separated)</label>
                  <input value={authors} onChange={e => setAuthors(e.target.value)} placeholder="Kaiming He, Jian Sun"
                    className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Year</label>
                  <input value={year} onChange={e => setYear(e.target.value)} placeholder="2016" type="number"
                    className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors" />
                </div>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Abstract (optional)</label>
                <textarea value={abstract} onChange={e => setAbstract(e.target.value)} rows={3}
                  placeholder="Paste the abstract here..."
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-blue-500/50 transition-colors resize-none" />
              </div>
              <Button onClick={handleUpload} loading={uploading} icon={<Upload className="w-4 h-4" />} className="w-full justify-center">
                {uploading ? 'Processing PDF...' : 'Upload & Index'}
              </Button>
            </div>
          </Card>

          <Card className="bg-blue-500/5 border-blue-500/20">
            <h3 className="text-sm font-medium text-blue-400 mb-2">What happens when you upload?</h3>
            <ol className="space-y-1.5 text-xs text-muted-foreground">
              {['PDF text is extracted (pypdf + pdfplumber fallback)', 'Text is split into overlapping chunks', 'Each chunk is embedded via Gemini text-embedding-004', 'Vectors stored in ChromaDB for fast retrieval', 'Paper saved to PostgreSQL — ready for chat'].map((s,i) => (
                <li key={i} className="flex gap-2"><span className="text-blue-400 font-mono flex-shrink-0">{i+1}.</span>{s}</li>
              ))}
            </ol>
          </Card>
        </div>
      ) : (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <Card className="bg-emerald-500/5 border-emerald-500/20 text-center py-10">
            <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-foreground mb-1">Successfully Indexed!</h2>
            <p className="text-muted-foreground text-sm">{result.title}</p>
            <p className="text-emerald-400 text-sm mt-2">{result.chunks_indexed} chunks embedded into ChromaDB</p>
          </Card>

          <Card>
            <p className="text-xs text-muted-foreground mb-2">Paper ID — use this in the Chat page</p>
            <div className="flex items-center gap-2 p-3 bg-secondary/50 rounded-xl border border-border">
              <code className="flex-1 text-xs text-blue-400 font-mono break-all">{result.paper_id}</code>
              <button onClick={copyId} className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
                <Copy className="w-4 h-4" />
              </button>
            </div>
          </Card>

          <div className="flex gap-3">
            <Link href={`/chat?paper_id=${result.paper_id}`} className="flex-1">
              <Button className="w-full justify-center" icon={<MessageSquare className="w-4 h-4" />}>Chat with this Paper</Button>
            </Link>
            <Button variant="secondary" onClick={() => { setResult(null); setFile(null); setTitle(''); setAuthors(''); setYear(''); setAbstract(''); }}>Upload Another</Button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
