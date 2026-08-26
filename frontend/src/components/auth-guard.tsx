"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ApiError } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { LoadingState } from "@/components/states";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const query = useUser();
  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) router.replace("/login");
  }, [query.error, router]);
  if (query.isLoading || !query.data) return <main className="mx-auto w-full max-w-5xl p-6"><LoadingState rows={6} /></main>;
  return children;
}
