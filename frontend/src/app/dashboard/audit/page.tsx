"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ShieldCheck, History, Eye, Terminal } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface AuditRecord {
  id: string;
  tenant_id: string;
  user_id?: string;
  user_email?: string;
  action: string;
  details: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export default function AuditPage() {
  const [selectedLog, setSelectedLog] = useState<AuditRecord | null>(null);

  // Fetch audit logs
  const { data: logs = [], isLoading } = useQuery<AuditRecord[]>({
    queryKey: ["audit_logs"],
    queryFn: () => api.get<AuditRecord[]>("/audit"),
    refetchInterval: 10000, // Refresh every 10 seconds for real-time security tracking!
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            Compliance Audit Trail
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time logs recording security access, administrative alterations, and authentication events.
          </p>
        </div>
      </div>

      {/* Logs Table Card */}
      <Card glass>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : logs.length === 0 ? (
            <EmptyState
              title="No Security Logs Recorded"
              description="Actions performed within your tenant organization will be logged here automatically."
              icon={<History className="h-6 w-6 text-muted-foreground" />}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Event Action</th>
                    <th className="py-3 px-4">IP Address</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {logs.map((log) => {
                    const dateStr = new Date(log.created_at).toLocaleString();
                    return (
                      <tr key={log.id} className="hover:bg-accent/5 transition-colors">
                        <td className="py-3.5 px-4 font-mono text-2xs text-muted-foreground">
                          {dateStr}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="font-semibold text-foreground">
                            {log.user_email || "System Thread"}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border ${
                            log.action.includes("create") || log.action.includes("seed")
                              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                              : log.action.includes("update")
                              ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                              : log.action.includes("delete")
                              ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                              : "bg-primary/10 border-primary/20 text-primary"
                          }`}>
                            {log.action.replace("_", " ")}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground">
                          {log.ip_address || "internal"}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedLog(log)}
                            className="h-8 gap-1.5 cursor-pointer text-xs"
                          >
                            <Eye className="h-3.5 w-3.5" /> Inspect
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* JSON Inspection Modal */}
      <Dialog
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title="Audit Event Details"
        description="Raw structural payload for compliance audits."
      >
        {selectedLog && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 p-3 bg-accent/10 border border-border rounded-lg text-xs">
              <Terminal className="h-4 w-4 text-primary" />
              <span className="font-mono text-muted-foreground">ID: {selectedLog.id}</span>
            </div>

            <pre className="p-4 bg-[#0a0a0f] border border-border rounded-xl text-2xs font-mono text-emerald-400 overflow-x-auto max-h-[300px] leading-relaxed select-all">
              {JSON.stringify(selectedLog.details, null, 2)}
            </pre>

            <div className="flex justify-end border-t border-border pt-4 mt-2">
              <Button onClick={() => setSelectedLog(null)}>
                Close Inspector
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
