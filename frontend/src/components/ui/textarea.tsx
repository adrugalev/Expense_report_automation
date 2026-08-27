import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, onInput, ...props },
  forwardedRef,
) {
  const localRef = React.useRef<HTMLTextAreaElement | null>(null);
  const setRef = React.useCallback((element: HTMLTextAreaElement | null) => {
    localRef.current = element;
    if (typeof forwardedRef === "function") forwardedRef(element);
    else if (forwardedRef) forwardedRef.current = element;
  }, [forwardedRef]);
  const resize = React.useCallback((element: HTMLTextAreaElement | null) => {
    if (!element) return;
    element.style.height = "auto";
    const borderHeight = element.offsetHeight - element.clientHeight;
    element.style.height = `${element.scrollHeight + borderHeight}px`;
  }, []);

  React.useLayoutEffect(() => resize(localRef.current));

  return (
    <textarea
      ref={setRef}
      className={cn(
        "min-h-24 w-full resize-none overflow-hidden rounded-md border border-border bg-surface px-3 py-2 text-sm [field-sizing:content] placeholder:text-muted disabled:opacity-60",
        className,
      )}
      onInput={(event) => {
        resize(event.currentTarget);
        onInput?.(event);
      }}
      {...props}
    />
  );
});
