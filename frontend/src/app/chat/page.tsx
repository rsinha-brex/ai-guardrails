"use client";

import { AppShell } from "@/components/AppShell";
import { ChatPanel } from "@/components/ChatPanel";
import { useBusinessId } from "@/lib/use-business-id";

export default function ChatPage() {
  const { businessId } = useBusinessId();
  return (
    <AppShell>
      {businessId ? (
        <ChatPanel businessId={businessId} />
      ) : (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-ink-muted">Loading…</p>
        </div>
      )}
    </AppShell>
  );
}
