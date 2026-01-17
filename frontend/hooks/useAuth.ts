/**
 * Auth hook for login, register, and token refresh.
 */

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api, handleApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";

// Types for API responses
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
}

interface AuthState {
  logout: () => void;
  setTokens: (accessToken: string, refreshToken: string, expiresIn: number) => void;
  setUser: (user: { id: string; email: string; fullName: string | null }) => void;
  refreshToken: string | null;
  accessToken: string | null;
  isTokenExpired: () => boolean;
}

export function useLogin() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();

  return useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }): Promise<{ tokens: TokenResponse; user: UserResponse }> => {
      const tokens = await api.auth.login(email, password) as TokenResponse;
      const user = await api.auth.me(tokens.access_token) as UserResponse;
      return { tokens, user };
    },
    onSuccess: ({ tokens, user }: { tokens: TokenResponse; user: UserResponse }) => {
      setTokens(tokens.access_token, tokens.refresh_token, tokens.expires_in);
      setUser({
        id: user.id,
        email: user.email,
        fullName: user.full_name,
      });
      toast.success("Welcome back!");
      router.push("/documents");
    },
    onError: handleApiError,
  });
}

export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: async ({
      email,
      password,
      fullName,
    }: {
      email: string;
      password: string;
      fullName?: string;
    }) => {
      return api.auth.register(email, password, fullName);
    },
    onSuccess: () => {
      toast.success("Account created! Please log in.");
      router.push("/login");
    },
    onError: handleApiError,
  });
}

export function useLogout() {
  const router = useRouter();
  const logout = useAuthStore((state: AuthState) => state.logout);

  return () => {
    logout();
    toast.success("Logged out");
    router.push("/login");
  };
}

export function useRefreshToken() {
  const { refreshToken, setTokens, logout } = useAuthStore();

  return useMutation({
    mutationFn: async (): Promise<TokenResponse> => {
      if (!refreshToken) throw new Error("No refresh token");
      return api.auth.refresh(refreshToken) as Promise<TokenResponse>;
    },
    onSuccess: (tokens: TokenResponse) => {
      setTokens(tokens.access_token, tokens.refresh_token, tokens.expires_in);
    },
    onError: () => {
      logout();
    },
  });
}

export function useAuthToken() {
  const { accessToken, isTokenExpired } = useAuthStore();
  const refreshMutation = useRefreshToken();

  // Return a function that gets a valid token
  return async (): Promise<string | null> => {
    if (!accessToken) return null;

    if (isTokenExpired()) {
      try {
        const result = await refreshMutation.mutateAsync();
        return result.access_token;
      } catch {
        return null;
      }
    }

    return accessToken;
  };
}
