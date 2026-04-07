"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ChatResponse, ChatSignal, Message, MovieResult, SignalMetric } from "@/lib/types";
import type { ReactNode } from "react";

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
  signal: undefined,
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
  const [expandedSignals, setExpandedSignals] = useState<Record<string, boolean>>({});
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
      signal: undefined,
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
        signal: data.signal,
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
    setExpandedSignals({});
    setError("");
    setDraft("");
  };

  const toggleResults = (messageId: string) => {
    setExpandedResults((current) => ({
      ...current,
      [messageId]: !current[messageId],
    }));
  };

  const toggleSignal = (messageId: string) => {
    setExpandedSignals((current) => ({
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
                    <MarkdownMessage content={message.content} />
                  </div>

                  {message.signal ? (
                    <SignalStrip
                      expanded={Boolean(expandedSignals[message.id])}
                      messageId={message.id}
                      onToggle={toggleSignal}
                      signal={message.signal}
                    />
                  ) : null}

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

function MarkdownMessage({ content }: { content: string }) {
  const blocks = parseMarkdownBlocks(content);

  return (
    <div className="message-markdown">
      {blocks.map((block, index) => {
        if (block.type === "ul") {
          return (
            <ul key={`ul-${index}`} className="message-list-block">
              {block.items.map((item, itemIndex) => (
                <li key={`ul-item-${index}-${itemIndex}`}>{renderInlineMarkdown(item)}</li>
              ))}
            </ul>
          );
        }

        if (block.type === "ol") {
          return (
            <ol key={`ol-${index}`} className="message-list-block">
              {block.items.map((item, itemIndex) => (
                <li key={`ol-item-${index}-${itemIndex}`}>{renderInlineMarkdown(item)}</li>
              ))}
            </ol>
          );
        }

        if (block.type === "heading") {
          return (
            <h3 key={`heading-${index}`} className="message-heading">
              {renderInlineMarkdown(block.text)}
            </h3>
          );
        }

        return (
          <p key={`p-${index}`} className="message-copy">
            {renderInlineMarkdown(block.text)}
          </p>
        );
      })}
    </div>
  );
}

function parseMarkdownBlocks(content: string) {
  const lines = content.split(/\r?\n/);
  const blocks: Array<
    | { type: "paragraph"; text: string }
    | { type: "heading"; text: string }
    | { type: "ul"; items: string[] }
    | { type: "ol"; items: string[] }
  > = [];

  let paragraph: string[] = [];
  let listType: "ul" | "ol" | null = null;
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) {
      return;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ").trim() });
    paragraph = [];
  };

  const flushList = () => {
    if (!listType || !listItems.length) {
      return;
    }
    blocks.push({ type: listType, items: listItems });
    listType = null;
    listItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const headingMatch = line.match(/^#{1,3}\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", text: headingMatch[1].trim() });
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (listType && listType !== "ul") {
        flushList();
      }
      listType = "ul";
      listItems.push(unorderedMatch[1].trim());
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      if (listType && listType !== "ol") {
        flushList();
      }
      listType = "ol";
      listItems.push(orderedMatch[1].trim());
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return blocks.length ? blocks : [{ type: "paragraph", text: content }];
}

function renderInlineMarkdown(text: string) {
  const segments: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const matched = match[0];
    const index = match.index ?? 0;

    if (index > lastIndex) {
      segments.push(text.slice(lastIndex, index));
    }

    if (matched.startsWith("**") && matched.endsWith("**")) {
      segments.push(
        <strong key={`${index}-strong`}>{matched.slice(2, -2)}</strong>,
      );
    } else if (matched.startsWith("`") && matched.endsWith("`")) {
      segments.push(
        <code key={`${index}-code`} className="message-code">
          {matched.slice(1, -1)}
        </code>,
      );
    }

    lastIndex = index + matched.length;
  }

  if (lastIndex < text.length) {
    segments.push(text.slice(lastIndex));
  }

  return segments.length ? segments : text;
}

function SignalStrip({
  signal,
  messageId,
  expanded,
  onToggle,
}: {
  signal: ChatSignal;
  messageId: string;
  expanded: boolean;
  onToggle: (messageId: string) => void;
}) {
  return (
    <div className="signal-strip">
      <button
        aria-expanded={expanded}
        className="signal-toggle"
        onClick={() => onToggle(messageId)}
        type="button"
      >
        <div className="signal-bars" aria-hidden="true">
          {signal.signals.map((metric) => (
            <span key={metric.label} className={`signal-bar signal-bar-${metric.band}`} />
          ))}
        </div>

        <span className="signal-label">signal {Math.round(signal.overall_score * 100)}</span>
      </button>

      {expanded ? <SignalDetails signal={signal} /> : null}
    </div>
  );
}

function SignalDetails({ signal }: { signal: ChatSignal }) {
  return (
    <div className="signal-panel">
      <div className="signal-grid">
        {signal.signals.map((metric) => (
          <SignalMetricRow key={metric.label} metric={metric} />
        ))}
      </div>

      <p className="signal-note">{signal.note}</p>

      <div className="signal-meta">
        <span>{signal.latency_ms} ms</span>
        <span>{signal.details.result_count} evidences</span>
        <span>{signal.details.llm_judge ? "judge on" : "judge off"}</span>
      </div>
    </div>
  );
}

function SignalMetricRow({ metric }: { metric: SignalMetric }) {
  return (
    <div className="signal-metric">
      <span>{metric.label}</span>
      <strong>{Math.round(metric.score * 100)}</strong>
    </div>
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
