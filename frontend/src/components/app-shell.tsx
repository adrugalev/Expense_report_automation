"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookUser, FileClock, FilePlus2, LogOut, Menu, Settings, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useUser } from "@/hooks/use-user";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { VersionDialog } from "@/components/version-dialog";

const adminNavigation = [
  { href: "/reports/new", label: "Новый отчёт", icon: FilePlus2 },
  { href: "/reports/history", label: "История", icon: FileClock },
  { href: "/employees", label: "Справочники", icon: BookUser },
  { href: "/settings", label: "Настройки", icon: Settings },
];

const employeeNavigation = [
  { href: "/reports/new", label: "Новый отчёт", icon: FilePlus2 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useUser();
  const navigation = user?.role === "employee" ? employeeNavigation : adminNavigation;
  const logout = useMutation({
    mutationFn: () => apiFetch<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => { queryClient.clear(); router.replace("/login"); },
  });
  const sidebar = (
    <div className="flex h-full flex-col bg-[var(--sidebar)] px-3 py-4 text-[var(--sidebar-foreground)]">
      <div className="flex min-h-12 items-center gap-3 px-2">
        <Image src="/huaxun-logo.png" alt="Huaxun" width={40} height={40} className="size-10 shrink-0 object-contain" priority />
        <div className="min-w-0 text-[13px] font-semibold leading-5">
          <span className="block">Автоматизация</span>
          <span className="block whitespace-nowrap">отчётных документов</span>
        </div>
      </div>
      <nav className="mt-6 space-y-1" aria-label="Основная навигация">
        {navigation.map((item) => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm text-white/65 hover:bg-white/8 hover:text-white",
                active && "bg-white/12 text-white",
              )}
            >
              <Icon className="size-4" />{item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-2 pt-6"><VersionDialog /></div>
    </div>
  );
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 lg:block">{sidebar}</aside>
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/45" onClick={() => setMobileOpen(false)} aria-label="Закрыть меню" />
          <aside className="relative h-full w-72">{sidebar}<Button variant="ghost" size="icon" className="absolute right-2 top-2 text-white" onClick={() => setMobileOpen(false)}><X className="size-5" /></Button></aside>
        </div>
      ) : null}
      <div className="min-w-0 lg:col-start-2">
        <header className="sticky top-0 z-30 flex h-16 items-center border-b border-border bg-surface/95 px-4 backdrop-blur sm:px-6">
          <Button variant="ghost" size="icon" className="mr-2 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Открыть меню"><Menu className="size-5" /></Button>
          <div className="ml-auto flex items-center gap-2">
            <div className="hidden text-right sm:block">
              <div className="text-sm font-medium">{user?.full_name}</div>
              <div className="text-xs text-muted">{user?.email}</div>
            </div>
            <ThemeToggle />
            <Button variant="ghost" size="icon" title="Выйти" aria-label="Выйти" onClick={() => logout.mutate()}><LogOut className="size-4" /></Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
