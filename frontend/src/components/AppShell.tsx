"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, type Business } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useBusinessId } from "@/lib/use-business-id";
import { ChevronDown } from "lucide-react";

const TABS = [
  { href: "/rules", label: "Rules" },
  { href: "/chat", label: "Chat" },
  { href: "/activity", label: "Activity" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { businessId: businessIdFromUrl, setBusinessId } = useBusinessId();

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [open, setOpen] = useState(false);
  const businessId = businessIdFromUrl || businesses[0]?.id || "";

  useEffect(() => {
    // Fail silently — the empty business list will surface as "no businesses
    // found" in the UI; logging to the browser console adds noise without
    // recovering from anything.
    api.businesses.list().then(setBusinesses).catch(() => {});
  }, []);

  const current = businesses.find((b) => b.id === businessId);

  const switchBusiness = (id: string) => {
    setBusinessId(id);
    setOpen(false);
  };

  const tabHref = (href: string) =>
    businessId ? `${href}?business=${businessId}` : href;

  return (
    <div className="flex flex-col flex-1 min-h-screen">
      <header className="bg-bg-elevated border-b border-border">
        <div className="mx-auto max-w-6xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="size-3 rounded-sm bg-accent" />
            <span className="font-display text-base text-ink">AI Guardrails</span>
            <span className="px-2 py-0.5 rounded-full bg-bg-subtle text-[11px] uppercase tracking-wide text-ink-muted font-mono">
              Demo
            </span>
          </div>
          <div className="relative">
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-2 py-1 text-sm hover:border-border-strong"
            >
              {current ? (
                <>
                  <span className="size-5 rounded-sm bg-accent-tint text-accent grid place-items-center text-[10px] font-semibold">
                    {current.name[0]}
                  </span>
                  <span className="text-ink">{current.name}</span>
                </>
              ) : (
                <span className="text-ink-muted">Select business</span>
              )}
              <ChevronDown className="size-3.5 text-ink-muted" />
            </button>
            {open && (
              <ul className="absolute right-0 mt-1 w-72 max-h-[70vh] overflow-y-auto overscroll-contain rounded-md border border-border bg-bg-elevated shadow-lg z-50">
                {businesses.map((b) => (
                  <li
                    key={b.id}
                    className={cn(
                      "px-3 py-2 text-sm cursor-pointer hover:bg-bg-subtle",
                      b.id === businessId && "bg-accent-tint text-accent",
                    )}
                    onClick={() => switchBusiness(b.id)}
                  >
                    <div className="font-medium">{b.name}</div>
                    <div className="text-xs text-ink-muted">{b.description}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <nav className="mx-auto max-w-6xl px-6 -mb-px flex gap-6">
          {TABS.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={tabHref(t.href)}
                className={cn(
                  "py-3 px-1 text-sm border-b-2",
                  active
                    ? "border-accent text-ink font-medium"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
