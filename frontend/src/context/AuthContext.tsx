import { createContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { User } from "../types";
import { loginUser, registerUser, getMe, api } from "../api/client";

interface RegisterData {
  email: string;
  password: string;
  name: string;
  company: string;
  title: string;
  ticket_type: string;
  interests: string[];
  goals: string;
  linkedin_url?: string;
  twitter_handle?: string;
  company_website?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  isAdmin: false,
  isLoading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setAuth = useCallback((newToken: string, newUser: User) => {
    localStorage.setItem("token", newToken);
    api.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    delete api.defaults.headers.common["Authorization"];
    setToken(null);
    setUser(null);
  }, []);

  // On mount: try to restore session from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      setIsLoading(false);
      return;
    }
    api.defaults.headers.common["Authorization"] = `Bearer ${stored}`;
    getMe()
      .then((me) => {
        setToken(stored);
        setUser(me);
      })
      .catch(() => {
        localStorage.removeItem("token");
        delete api.defaults.headers.common["Authorization"];
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await loginUser(email, password);
      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
      const me = await getMe();
      setAuth(access_token, me);
    },
    [setAuth]
  );

  const register = useCallback(
    async (data: RegisterData) => {
      const { access_token } = await registerUser(data);
      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
      const me = await getMe();
      setAuth(access_token, me);
    },
    [setAuth]
  );

  const refreshUser = useCallback(async () => {
    const me = await getMe();
    setUser(me);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isAdmin: user?.is_admin ?? false,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
