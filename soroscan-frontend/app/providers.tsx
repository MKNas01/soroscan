"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/context/ToastContext";
import { ApolloProvider } from "@/providers/ApolloProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ThemeProvider>
      <ApolloProvider>
        <ToastProvider>{children}</ToastProvider>
      </ApolloProvider>
    </ThemeProvider>
  );
}