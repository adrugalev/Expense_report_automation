"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { PageHeader } from "@/components/page-header";
import { cn } from "@/lib/utils";

const modes = [
  { value: "light", label: "Светлая", icon: Sun },
  { value: "dark", label: "Тёмная", icon: Moon },
  { value: "system", label: "Системная", icon: Laptop },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  return (
    <>
      <PageHeader title="Настройки" description="Параметры отображения этого устройства." />
      <section className="max-w-xl border-y border-border py-5">
        <h2 className="text-sm font-semibold">Тема интерфейса</h2>
        <div className="mt-3 grid grid-cols-3 gap-2" role="radiogroup" aria-label="Тема интерфейса">
          {modes.map(({ value, label, icon: Icon }) => (
            <button key={value} role="radio" aria-checked={theme === value} onClick={() => setTheme(value)} className={cn("flex h-20 flex-col items-center justify-center gap-2 rounded-md border border-border bg-surface text-sm hover:bg-surface-muted", theme === value && "border-primary bg-primary-soft text-primary")}>
              <Icon className="size-5" />{label}
            </button>
          ))}
        </div>
      </section>
    </>
  );
}
