import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that don't require authentication
const publicRoutes = ["/", "/login", "/register"];

// Routes that should redirect to dashboard if already authenticated
const authRoutes = ["/", "/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for auth token in cookies (set by the client-side auth store)
  // Note: In production, you might want to verify the token server-side
  const hasAuthToken = request.cookies.has("resume-crafter-auth");

  // If trying to access auth routes while logged in, redirect to dashboard
  if (authRoutes.includes(pathname) && hasAuthToken) {
    return NextResponse.redirect(new URL("/documents", request.url));
  }

  // If trying to access protected routes without auth, redirect to login
  if (!publicRoutes.includes(pathname) && !hasAuthToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!api|_next/static|_next/image|favicon.ico|public).*)",
  ],
};
