"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";

export function useUser() {
  return useQuery({ queryKey: ["current-user"], queryFn: () => apiFetch<User>("/auth/me"), retry: false });
}
