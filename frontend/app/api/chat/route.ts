import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const REQUEST_TIMEOUT_MS = 180000;

const API_URLS = [
  process.env.MOVIEMATE_API_URL,
  process.env.NEXT_PUBLIC_MOVIEMATE_API_URL,
  "http://127.0.0.1:8000",
].filter((value, index, array): value is string => Boolean(value) && array.indexOf(value) === index);

type BackendResult = {
  answer: string;
  intent: string;
  show_movie_cards?: boolean;
  signal?: unknown;
  results: unknown[];
};

function normalizeBaseUrl(url: string) {
  return url.replace(/\/+$/, "");
}

async function parseResponse(response: Response) {
  const text = await response.text();

  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text) as BackendResult | { error?: string; detail?: string };
  } catch {
    return { error: text };
  }
}

async function postToBackend(url: string, body: unknown) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${normalizeBaseUrl(url)}/chat`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: controller.signal,
    });

    const data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(
        (data as { detail?: string; error?: string } | null)?.detail ??
          (data as { error?: string } | null)?.error ??
          `MovieMate backend request failed with status ${response.status}.`,
      );
    }

    if (!data || typeof data !== "object" || !("answer" in data)) {
      throw new Error("MovieMate backend returned an empty or unexpected response.");
    }

    return data;
  } finally {
    clearTimeout(timeout);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    if (!body?.session_id || !body?.message) {
      return NextResponse.json(
        { error: "session_id and message are required." },
        { status: 400 },
      );
    }

    let lastError = "MovieMate backend request failed.";

    for (const apiUrl of API_URLS) {
      try {
        const data = await postToBackend(apiUrl, body);
        return NextResponse.json(data, {
          headers: {
            "x-moviemate-backend": apiUrl,
          },
        });
      } catch (error) {
        lastError = error instanceof Error ? error.message : lastError;
      }
    }

    return NextResponse.json(
      {
        error: lastError,
      },
      { status: 502 },
    );
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Unable to reach the MovieMate backend. Confirm the FastAPI server is running and MOVIEMATE_API_URL is correct.",
      },
      { status: 502 },
    );
  }
}
