"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, AuthToken, UserRole } from "./types";
import { apiRequest } from "./api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isOfficial: boolean;
  isInstitution: boolean;
  isAdmin: boolean;
  isAuditor: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("aicte_token");
    if (savedToken) {
      setToken(savedToken);
      fetchCurrentUser(savedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchCurrentUser = async (authToken: string) => {
    try {
      const userData = await apiRequest<User>("/auth/me", {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      setUser(userData);
    } catch {
      if (typeof window !== "undefined") {
        localStorage.removeItem("aicte_token");
      }
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await apiRequest<AuthToken>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      localStorage.setItem("aicte_token", data.access_token);
      setToken(data.access_token);

      const currentUser: User = {
        id: data.user_id,
        email,
        role: data.role,
        full_name: data.full_name,
        institution_id: data.institution_id,
        is_active: true,
      };
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("aicte_token");
      sessionStorage.clear();
    }
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.replace("/login");
    }
  };

  const isOfficial = user?.role === "official" || user?.role === "admin";
  const isInstitution = user?.role === "institution";
  const isAdmin = user?.role === "admin";
  const isAuditor = user?.role === "auditor" || user?.role === "admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        isOfficial,
        isInstitution,
        isAdmin,
        isAuditor,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
