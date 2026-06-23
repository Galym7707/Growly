"use client";

import { useCallback, useState } from "react";
import { Icon } from "@/components/icons";

export type ToastTone = "success" | "error";

export type ToastItem = {
  id: number;
  tone: ToastTone;
  message: string;
};

let toastSeq = 0;

/** Minimal local toast queue: push a message, it auto-dismisses after 4s. */
export function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastTone, message: string) => {
      toastSeq += 1;
      const id = toastSeq;
      setToasts((current) => [...current, { id, tone, message }]);
      window.setTimeout(() => dismiss(id), 4000);
    },
    [dismiss],
  );

  return { toasts, push, dismiss };
}

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  if (!toasts.length) return null;
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <div className={`toast toast-${toast.tone}`} key={toast.id} role="status">
          <Icon name={toast.tone === "success" ? "check" : "close"} />
          <span>{toast.message}</span>
          <button
            aria-label="Закрыть"
            className="toast-close"
            onClick={() => onDismiss(toast.id)}
            type="button"
          >
            <Icon name="close" />
          </button>
        </div>
      ))}
    </div>
  );
}
