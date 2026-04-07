export type MovieResult = {
  tconst: string;
  title: string;
  year: number | null;
  genres: string | null;
  rating: number | null;
  runtime_minutes: number | null;
  rerank_score: number | null;
};

export type SignalBand = "low" | "medium" | "high";

export type SignalMetric = {
  label: string;
  score: number;
  band: SignalBand;
};

export type ChatSignal = {
  overall_score: number;
  band: SignalBand;
  latency_ms: number;
  note: string;
  signals: SignalMetric[];
  details: {
    retrieval_algorithmic?: {
      score: number;
      band: SignalBand;
      note: string;
      result_count: number;
      filter_alignment: number;
      query_overlap: number;
    } | null;
    llm_judge?: {
      retrieval_relevance: number;
      evidence_alignment: number;
      groundedness: number;
      helpfulness: number;
      presentation_discipline: number;
      note: string;
    } | null;
    result_count: number;
    show_movie_cards: boolean;
  };
};

export type ChatResponse = {
  answer: string;
  intent: string;
  show_movie_cards?: boolean;
  signal?: ChatSignal;
  results: MovieResult[];
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  showMovieCards?: boolean;
  signal?: ChatSignal;
  results: MovieResult[];
};
