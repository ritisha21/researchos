import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RoadmapRequest { topic: string; force_refresh?: boolean; }
export interface PaperReference { title: string; authors: string[]; year?: number; url?: string; why_important?: string; }
export interface LearningStep { order: number; topic: string; description: string; estimated_hours?: number; }
export interface RoadmapResponse {
  id: string; topic: string; topic_display: string;
  prerequisites: string[]; learning_path: LearningStep[];
  foundational_papers: PaperReference[]; intermediate_papers: PaperReference[];
  advanced_papers: PaperReference[]; research_frontiers: string[];
  research_gaps: string[]; recommended_reading_order: string[];
  generated_by_model: string; cached: boolean; created_at: string;
}

export interface PaperSearchResult {
  title: string; authors: string[]; year?: number; abstract?: string;
  citation_count: number; url?: string; source: string;
  external_id: string; doi?: string; arxiv_id?: string; semantic_scholar_id?: string;
}
export interface PaperSearchResponse { query: string; total_results: number; sources_queried: string[]; results: PaperSearchResult[]; }

export interface SummariseResponse { title: string; summary: string; key_contributions: string[]; limitations: string[]; future_work: string[]; cached: boolean; }
export interface ExplainResponse { title: string; explanation: string; cached: boolean; }
export interface NotesResponse { title: string; notes: string[]; cached: boolean; }
export interface TakeawaysResponse { title: string; takeaways: string[]; cached: boolean; }
export interface LiteratureReviewResponse { papers_reviewed: number; review: string; themes: string[]; gaps: string[]; recommended_reading_order: string[]; }

export interface UploadResponse { paper_id: string; title: string; chunks_indexed: number; file_size_bytes: number; message: string; }

export interface Citation { chunk_index: number; page?: number; text_snippet: string; relevance_score: number; }
export interface ChatResponse { answer: string; citations: Citation[]; paper_id: string; question: string; }

// ── API calls ─────────────────────────────────────────────────────────────────

export const generateRoadmap = (req: RoadmapRequest) =>
  api.post<RoadmapResponse>('/api/v1/roadmap', req).then(r => r.data);

export const searchPapers = (query: string, limit = 10, sort_by = 'relevance') =>
  api.get<PaperSearchResponse>('/api/v1/papers/search', { params: { q: query, limit, sort_by } }).then(r => r.data);

export const summarisePaper = (title: string, abstract?: string, force_refresh = false) =>
  api.post<SummariseResponse>('/api/v1/papers/summarise', { title, abstract, force_refresh }).then(r => r.data);

export const explainPaper = (title: string, abstract?: string) =>
  api.post<ExplainResponse>('/api/v1/papers/explain', { title, abstract }).then(r => r.data);

export const getNotes = (title: string, abstract?: string) =>
  api.post<NotesResponse>('/api/v1/papers/notes', { title, abstract }).then(r => r.data);

export const getTakeaways = (title: string, abstract?: string) =>
  api.post<TakeawaysResponse>('/api/v1/papers/takeaways', { title, abstract }).then(r => r.data);

export const getLiteratureReview = (titles: string[], abstracts?: string[], focus?: string) =>
  api.post<LiteratureReviewResponse>('/api/v1/papers/literature-review', { titles, abstracts, focus }).then(r => r.data);

export const uploadPdf = (formData: FormData) =>
  api.post<UploadResponse>('/api/v1/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);

export const chatWithPaper = (paper_id: string, question: string, history: {role:string;content:string}[] = []) =>
  api.post<ChatResponse>('/api/v1/chat', { paper_id, question, conversation_history: history }).then(r => r.data);
