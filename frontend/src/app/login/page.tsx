"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const schema = z.object({ email: z.email("Укажите корректный email"), password: z.string().min(8, "Минимум 8 символов") });
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const form = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const login = useMutation({
    mutationFn: (values: FormData) => apiFetch<{ user: User }>("/auth/login", { method: "POST", body: JSON.stringify(values) }),
    onSuccess: (data) => { queryClient.setQueryData(["current-user"], data.user); router.replace("/"); },
  });
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-md bg-primary text-white"><FileText className="size-5" /></div>
          <div><h1 className="text-lg font-semibold">Отчётные документы</h1><p className="text-sm text-muted">Вход в рабочее пространство</p></div>
        </div>
        <Card className="p-5">
          <form className="space-y-4" onSubmit={form.handleSubmit((values) => login.mutate(values))}>
            <label className="block text-sm font-medium">Email<Input className="mt-1.5" type="email" autoComplete="email" {...form.register("email")} /></label>
            {form.formState.errors.email ? <p className="text-xs text-danger">{form.formState.errors.email.message}</p> : null}
            <label className="block text-sm font-medium">Пароль<Input className="mt-1.5" type="password" autoComplete="current-password" {...form.register("password")} /></label>
            {form.formState.errors.password ? <p className="text-xs text-danger">{form.formState.errors.password.message}</p> : null}
            {login.error ? <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-danger dark:bg-red-950/40">{login.error.message}</p> : null}
            <Button className="w-full" disabled={login.isPending}>{login.isPending ? <Loader2 className="size-4 animate-spin" /> : null}Войти</Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
