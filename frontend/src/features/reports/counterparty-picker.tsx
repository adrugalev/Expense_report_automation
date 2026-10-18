"use client";

import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface CounterpartyPickerProps {
  value: string;
  options: string[];
  open: boolean;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSelect: (value: string) => void;
  onOpenChange: (open: boolean) => void;
}

export function CounterpartyPicker({ value, options, open, disabled, onChange, onSelect, onOpenChange }: CounterpartyPickerProps) {
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const [search, setSearch] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const enabled = options.length > 0;
  const visible = enabled && open && !disabled;
  const matches = options.filter((option) => option.toLocaleLowerCase().includes(search.toLocaleLowerCase()));

  useEffect(() => {
    if (!visible) return;
    input.current?.focus();
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) onOpenChange(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [onOpenChange, visible]);

  useEffect(() => {
    if (visible && activeIndex >= 0) document.getElementById(`${listId}-${activeIndex}`)?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex, listId, visible]);

  const showOptions = () => {
    setSearch("");
    setActiveIndex(-1);
    onOpenChange(true);
  };
  const select = (option: string) => {
    onChange(option);
    onSelect(option);
    onOpenChange(false);
    setSearch("");
    setActiveIndex(-1);
  };

  return <div ref={root} className="relative">
    <Input
      ref={input}
      aria-label="Контрагент / организация"
      role={enabled ? "combobox" : undefined}
      aria-expanded={enabled ? visible : undefined}
      aria-controls={visible ? listId : undefined}
      aria-autocomplete={enabled ? "list" : undefined}
      aria-activedescendant={visible && activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
      autoComplete="off"
      value={value}
      disabled={disabled}
      className={enabled ? "pr-11" : undefined}
      onFocus={() => { if (enabled && !open) showOptions(); }}
      onChange={(event) => {
        onChange(event.target.value);
        setSearch(event.target.value.trim());
        setActiveIndex(-1);
        if (enabled) onOpenChange(true);
      }}
      onKeyDown={(event) => {
        if (!enabled) return;
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          if (!visible) showOptions();
          setActiveIndex((current) => event.key === "ArrowDown" ? Math.min(current + 1, matches.length - 1) : Math.max(current - 1, 0));
        } else if (event.key === "Escape") {
          event.preventDefault();
          onOpenChange(false);
        } else if (event.key === "Enter" && visible) {
          event.preventDefault();
          const option = matches[activeIndex] ?? matches.find((item) => item.toLocaleLowerCase() === value.trim().toLocaleLowerCase());
          if (option) select(option);
          else onOpenChange(false);
        } else if (event.key === "Tab") {
          onOpenChange(false);
        }
      }}
    />
    {enabled ? <Button
      type="button" variant="ghost" size="icon"
      className="absolute right-1 top-1 text-muted"
      title="Выбрать контрагента" aria-label="Выбрать контрагента"
      aria-expanded={visible} aria-controls={visible ? listId : undefined}
      disabled={disabled}
      onMouseDown={(event) => event.preventDefault()}
      onClick={(event) => { event.preventDefault(); if (visible) onOpenChange(false); else showOptions(); }}
    ><ChevronDown className="size-4" /></Button> : null}
    {visible ? <div id={listId} role="listbox" aria-label="Контрагенты" className="absolute z-40 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-border bg-surface p-1 shadow-lg">
      {matches.map((option, index) => <button
        key={option} id={`${listId}-${index}`} type="button" role="option" tabIndex={-1}
        aria-selected={value === option}
        className={cn("flex min-h-8 w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-muted", activeIndex === index && "bg-surface-muted")}
        onMouseDown={(event) => event.preventDefault()}
        onMouseMove={() => setActiveIndex(index)}
        onClick={(event) => { event.preventDefault(); select(option); }}
      ><Check className={cn("size-4 shrink-0 text-primary", value !== option && "invisible")} /><span className="min-w-0 break-words">{option}</span></button>)}
      {!matches.length ? <p className="px-2 py-3 text-sm text-muted">Нет совпадений</p> : null}
    </div> : null}
  </div>;
}
