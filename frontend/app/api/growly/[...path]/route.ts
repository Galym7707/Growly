import { createServerClient } from "@supabase/ssr";
import { NextRequest, NextResponse } from "next/server";

type WorkspaceHeaders =
  | { headers: Headers }
  | { response: NextResponse };

async function resolveWorkspaceHeaders(
  request: NextRequest,
): Promise<WorkspaceHeaders> {
  const headers = new Headers();
  const authRequired = process.env.NEXT_PUBLIC_AUTH_REQUIRED === "true";
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!authRequired || !supabaseUrl || !supabaseKey) {
    headers.set("X-Growly-Workspace-Id", "local");
    return { headers };
  }

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll() {
        // Session refresh is handled by frontend/proxy.ts.
      },
    },
  });
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return {
      response: NextResponse.json(
        { detail: "Требуется вход в Growly." },
        { status: 401 },
      ),
    };
  }
  headers.set("X-Growly-Workspace-Id", data.user.id);
  if (data.user.email) {
    headers.set("X-Growly-User-Email", data.user.email);
  }
  return { headers };
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const baseUrl =
    process.env.GROWLY_API_URL ||
    process.env.NEXT_PUBLIC_GROWLY_API_URL ||
    "http://localhost:8000";
  const target = new URL(`/api/${path.join("/")}`, baseUrl);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.append(key, value);
  });

  const headers = new Headers();
  headers.set("Accept", "application/json");
  const apiKey = process.env.GROWLY_API_KEY;
  if (apiKey) headers.set("X-Growly-API-Key", apiKey);
  const workspace = await resolveWorkspaceHeaders(request);
  if ("response" in workspace) return workspace.response;
  workspace.headers.forEach((value, key) => {
    headers.set(key, value);
  });
  const hasBody = !["GET", "HEAD"].includes(request.method);
  if (hasBody) headers.set("Content-Type", "application/json");

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(360_000),
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Не удалось подключиться к Growly API. Проверьте адрес бэкенда и его состояние.",
      },
      { status: 502 },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const maxDuration = 300;
