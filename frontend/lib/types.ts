export type MovieResult = {
  tconst: string;
  title: string;
  year: number | null;
  genres: string | null;
  rating: number | null;
  runtime_minutes: number | null;
  rerank_score: number | null;
};

export type ChatResponse = {
  answer: string;
  intent: string;
  results: MovieResult[];
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  results: MovieResult[];
};
