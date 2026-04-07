"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ChatResponse, Message, MovieResult } from "@/lib/types";

const STORAGE_KEY = "moviemate-ui-state";
const THEME_KEY = "moviemate-theme";

const heroPhrases = [
  "moviemate",
  'movies like "Prisoners" but a little faster',
  "feel-good films under two hours",
  "smart sci-fi with strong visuals",
  "hidden gems with high IMDb ratings",
];

const starterPrompts = [
  "Recommend mind-bending sci-fi movies with strong visuals",
  "I loved Zodiac and Prisoners. Give me darker thrillers",
  "Feel-good movies under 2 hours for a weekend night",
  "Suggest hidden gems like Whiplash or Black Swan",
];

const createId = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const initialAssistantMessage: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi, I'm moviemate. Ask for recommendations by mood, genre, actor, runtime, or a movie you already like.",
  intent: "greeting",
  showMovieCards: false,
  results: [],
};

export function ChatDashboard() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([initialAssistantMessage]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [expandedResults, setExpandedResults] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const typingText = useLoopingTypewriter(heroPhrases);
  const showStarterState = messages.length === 1;

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);

    if (!saved) {
      setSessionId(createId());
      return;
    }

    try {
      const parsed = JSON.parse(saved) as {
        sessionId?: string;
        messages?: Message[];
      };

      setSessionId(parsed.sessionId || createId());
      setMessages(parsed.messages?.length ? parsed.messages : [initialAssistantMessage]);
    } catch {
      setSessionId(createId());
    }
  }, []);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem(THEME_KEY);

    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
      return;
    }

    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(prefersDark ? "dark" : "light");
  }, []);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sessionId,
        messages,
      }),
    );
  }, [messages, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [loading, messages]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading || !sessionId) {
      return;
    }

    const userMessage: Message = {
      id: createId(),
      role: "user",
      content: trimmed,
      showMovieCards: false,
      results: [],
    };

    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
        }),
      });

      const data = (await response.json()) as ChatResponse | { error?: string };

      if (!response.ok) {
        throw new Error((data as { error?: string }).error || "MovieMate could not answer that request.");
      }

      if (!("answer" in data)) {
        throw new Error("MovieMate returned an unexpected response.");
      }

      const assistantMessage: Message = {
        id: createId(),
        role: "assistant",
        content: data.answer,
        intent: data.intent,
        showMovieCards: data.show_movie_cards ?? false,
        results: data.results,
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unexpected frontend error.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await sendMessage(draft);
  };

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await sendMessage(draft);
    }
  };

  const resetSession = () => {
    const nextSession = createId();
    setSessionId(nextSession);
    setMessages([initialAssistantMessage]);
    setExpandedResults({});
    setError("");
    setDraft("");
  };

  const toggleResults = (messageId: string) => {
    setExpandedResults((current) => ({
      ...current,
      [messageId]: !current[messageId],
    }));
  };

  return (
    <main className="chat-page">
      <div className="app-shell">
        <header className="app-header">
          <div className="brand-block">
            <span className="brand-mark">m</span>
            <div>
              <h1>moviemate</h1>
              <p>Minimal AI movie search with clean chat and recommendation cards.</p>
            </div>
          </div>

          <div className="header-actions">
            <div className="theme-toggle" aria-label="Theme toggle">
              <button
                className={`theme-option ${theme === "light" ? "theme-option-active" : ""}`}
                onClick={() => setTheme("light")}
                type="button"
              >
                Light
              </button>
              <button
                className={`theme-option ${theme === "dark" ? "theme-option-active" : ""}`}
                onClick={() => setTheme("dark")}
                type="button"
              >
                Dark
              </button>
            </div>

            <button className="ghost-button" onClick={resetSession} type="button">
              New chat
            </button>
          </div>
        </header>

        <section className="hero-card">
          <p className="eyebrow">AI movie discovery</p>
          <h2>moviemate</h2>
          <p className="hero-copy">
            A clean, client-ready movie assistant that feels familiar, responds fast, and turns
            each answer into easy-to-scan picks.
          </p>

          <div className="type-line" aria-live="polite">
            <span className="type-label">Try:</span>
            <span className="type-text">{typingText}</span>
            <span className="type-caret" aria-hidden="true" />
          </div>

          {showStarterState ? (
            <div className="prompt-list">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  className="prompt-chip"
                  onClick={() => void sendMessage(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <section className="chat-card">
          <div className="message-list">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`message-row ${message.role === "user" ? "message-row-user" : "message-row-assistant"}`}
              >
                {message.role === "assistant" ? <span className="message-avatar">m</span> : null}

                <div className="message-stack">
                  <span className="message-name">{message.role === "user" ? "You" : "moviemate"}</span>

                  <div className={`message-bubble ${message.role === "user" ? "message-bubble-user" : "message-bubble-assistant"}`}>
                    <p className="message-copy">{message.content}</p>
                  </div>

                  {message.showMovieCards && message.results.length > 0 ? (
                    <div className="results-section">
                      <button
                        className="results-toggle"
                        onClick={() => toggleResults(message.id)}
                        type="button"
                      >
                        {expandedResults[message.id] ? "Hide movie cards" : `Show movie cards (${message.results.length})`}
                      </button>

                      {expandedResults[message.id] ? (
                        <div className="movie-grid">
                          {message.results.map((movie) => (
                            <MovieCard key={movie.tconst} movie={movie} />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </article>
            ))}

            {loading ? (
              <article className="message-row message-row-assistant">
                <span className="message-avatar">m</span>

                <div className="message-stack">
                  <span className="message-name">moviemate</span>
                  <div className="message-bubble message-bubble-assistant loading-bubble">
                    <div className="thinking-state">
                      <div className="thinking-bars" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                      </div>
                      <p>Finding the best fit for your prompt...</p>
                    </div>
                  </div>
                </div>
              </article>
            ) : null}

            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            {error ? <p className="error-banner">{error}</p> : null}

            <div className="composer-shell">
              <textarea
                id="moviemate-prompt"
                className="composer-input"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask for a genre, mood, actor, runtime, or movies like something you love"
                rows={3}
                value={draft}
              />

              <div className="composer-footer">
                <span className="helper-text">Enter to send. Shift+Enter for a new line.</span>
                <button className="primary-button" disabled={loading || !draft.trim()} type="submit">
                  {loading ? "Thinking..." : "Send"}
                </button>
              </div>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

function useLoopingTypewriter(phrases: string[]) {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!phrases.length) {
      return;
    }

    const currentPhrase = phrases[phraseIndex] ?? "";
    const isFullyTyped = displayText === currentPhrase;
    const isCleared = displayText.length === 0;

    const timeout = window.setTimeout(
      () => {
        if (!isDeleting) {
          if (!isFullyTyped) {
            setDisplayText(currentPhrase.slice(0, displayText.length + 1));
            return;
          }

          setIsDeleting(true);
          return;
        }

        if (!isCleared) {
          setDisplayText(currentPhrase.slice(0, displayText.length - 1));
          return;
        }

        setIsDeleting(false);
        setPhraseIndex((currentIndex) => (currentIndex + 1) % phrases.length);
      },
      isDeleting ? 40 : isFullyTyped ? 1350 : 68,
    );

    return () => window.clearTimeout(timeout);
  }, [displayText, isDeleting, phraseIndex, phrases]);

  return displayText;
}

function MovieCard({ movie }: { movie: MovieResult }) {
  return (
    <article className="movie-card">
      <div className="movie-card-topline">
        <span className="movie-badge">IMDb</span>
        <strong>{formatRating(movie.rating)}</strong>
      </div>

      <h3>{movie.title}</h3>
      <p className="movie-meta">{formatMeta(movie.year, movie.runtime_minutes)}</p>
      <p className="movie-genres">{movie.genres || "Genre not available"}</p>
    </article>
  );
}

function formatRating(rating: number | null) {
  if (typeof rating !== "number") {
    return "N/A";
  }

  return `${rating.toFixed(1)}/10`;
}

function formatMeta(year: number | null, runtime: number | null) {
  const parts = [] as string[];

  if (year) {
    parts.push(String(year));
  }

  if (runtime) {
    parts.push(`${runtime} min`);
  }

  return parts.join(" • ") || "Details unavailable";
}
