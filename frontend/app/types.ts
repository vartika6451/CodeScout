export interface Repository {
  repository: string;
  total_chunks: number;
  total_files: number;
  language?: string;
  stars?: number;
}

export interface AnalyzeResult {
  message: string;
  repository: string;
  owner: string;
  language: string;
  stars: number;
  total_files: number;
  total_chunks: number;
  embeddings_created: number;
}

export interface SourceCitation {
  file_path: string;
  chunk_index: number;
  similarity: number;
  content?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: SourceCitation[];
  refined_question?: string;
  attempt_count?: number;
  isError?: boolean;
}
