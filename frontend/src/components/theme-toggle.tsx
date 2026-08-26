"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const modes = [
  { value: "light", icon: Sun, label: "Светлая тема" },
  { value: "dark", icon: Moon, label: "Тёмная тема" },
  { value: "system", icon: Laptop, label: "Системная тема" },
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const index = Math.max(0, modes.findIndex((mode) => mode.value === (theme ?? "system")));
  const current = modes[index];
  const Icon = current.icon;
  return (
    <Button
      size="icon"
      variant="ghost"
      title={current.label}
      aria-label={current.label}
      onClick={() => setTheme(modes[(index + 1) % modes.length].value)}
    >
      <Icon className="size-4" />
    </Button>
  );
}
