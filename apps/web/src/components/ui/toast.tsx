"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (title: string, description?: string, type?: ToastType) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((title: string, description?: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, title, description, type }]);

    // Auto-remove after 4 seconds
    setTimeout(() => removeToast(id), 4000);
  }, [removeToast]);

  const success = useCallback((title: string, description?: string) => toast(title, description, "success"), [toast]);
  const error = useCallback((title: string, description?: string) => toast(title, description, "error"), [toast]);
  const info = useCallback((title: string, description?: string) => toast(title, description, "info"), [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error, info }}>
      {children}
      
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85, transition: { duration: 0.15 } }}
              className="pointer-events-auto w-full glass p-4 rounded-lg shadow-lg flex items-start gap-3 border border-border"
            >
              <div className="mt-0.5 flex-shrink-0">
                {t.type === "success" && <CheckCircle className="h-5 w-5 text-emerald-500" />}
                {t.type === "error" && <AlertCircle className="h-5 w-5 text-rose-500" />}
                {t.type === "info" && <Info className="h-5 w-5 text-primary" />}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">{t.title}</p>
                {t.description && (
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{t.description}</p>
                )}
              </div>

              <button
                onClick={() => removeToast(t.id)}
                className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
