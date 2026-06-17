import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { isAuthRequired } from "@/lib/auth-config";

const protectedPrefixes = [
  "/dashboard",
  "/chat",
  "/market-scan",
  "/reports",
  "/content-plan",
  "/drafts",
  "/sources",
  "/settings",
  "/tg",
  "/api/growly",
];

export async function proxy(request: NextRequest) {
  const authRequired = isAuthRequired();
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const isProtected = protectedPrefixes.some((prefix) =>
    request.nextUrl.pathname.startsWith(prefix),
  );
  if (!authRequired) {
    return NextResponse.next({ request });
  }
  if (!supabaseUrl || !supabaseKey) {
    if (!isProtected) {
      return NextResponse.next({ request });
    }
    return denyAccess(request);
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet, headers) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
        Object.entries(headers).forEach(([key, value]) => {
          response.headers.set(key, value);
        });
      },
    },
  });
  const { data } = await supabase.auth.getUser();
  if (!data.user && isProtected) {
    return denyAccess(request);
  }
  return response;
}

function denyAccess(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json(
      { detail: "Требуется вход в Growly." },
      { status: 401 },
    );
  }
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
