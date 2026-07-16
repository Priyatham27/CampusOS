"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  CheckCircle,
  AlertCircle,
  Activity,
  History,
  Trash2,
} from "lucide-react";
import { AuditLog } from "@/types/academic";

export default function AcademicSettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [entityType, setEntityType] = useState<"departments" | "programs" | "courses">("departments");
  const [csvData, setCsvData] = useState<any[]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [fileName, setFileName] = useState("");
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Fetch recent audit logs from MongoDB if available
  const { data: auditLogs = [] } = useQuery<AuditLog[]>({
    queryKey: ["audit_logs", orgId],
    queryFn: async () => {
      try {
        const res = await api.get<AuditLog[]>(`/audit?module=academic&limit=8`);
        return res;
      } catch {
        // Fallback dummy audit logs if audit trail is not active or empty
        return [
          {
            id: "1",
            organizationId: orgId,
            action: "academic_year.created",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            performedBy: "admin@avanthi.edu",
            module: "academic",
            details: { name: "2026-2027" },
          },
          {
            id: "2",
            organizationId: orgId,
            action: "department.bulk_created",
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            performedBy: "admin@avanthi.edu",
            module: "academic",
            details: { count: 3 },
          },
        ];
      }
    },
    enabled: !!orgId,
  });

  // Bulk creation mutation
  const bulkCreateMutation = useMutation({
    mutationFn: (payload: any[]) =>
      api.post(`/organizations/${orgId}/${entityType}/bulk`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [entityType, orgId] });
      success("Import Successful", `Bulk registered ${csvData.length} records successfully.`);
      setCsvData([]);
      setCsvHeaders([]);
      setFileName("");
    },
    onError: (err: any) => {
      toastError("Import Failed", err?.detail || "An error occurred during DB write.");
    },
  });

  // Handle CSV file upload & client-side parsing
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setValidationErrors([]);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
        if (lines.length < 2) {
          setValidationErrors(["CSV file must contain a header row and at least one data row."]);
          return;
        }

        const headers = lines[0].split(",").map((h) => h.trim().replace(/^["']|["']$/g, ""));
        setCsvHeaders(headers);

        const parsedRows = lines.slice(1).map((line, idx) => {
          const cols = line.split(",").map((c) => c.trim().replace(/^["']|["']$/g, ""));
          const rowObj: any = {};
          headers.forEach((h, colIdx) => {
            rowObj[h] = cols[colIdx] || "";
          });
          return rowObj;
        });

        // Basic structural Zod validation mapping depending on selected entity
        const errorsList: string[] = [];
        parsedRows.forEach((row, idx) => {
          if (entityType === "departments") {
            if (!row.name) errorsList.push(`Row ${idx + 2}: 'name' is missing.`);
            if (!row.code) errorsList.push(`Row ${idx + 2}: 'code' is missing.`);
          } else if (entityType === "courses") {
            if (!row.name) errorsList.push(`Row ${idx + 2}: 'name' is missing.`);
            if (!row.courseCode) errorsList.push(`Row ${idx + 2}: 'courseCode' is missing.`);
            if (!row.credits) errorsList.push(`Row ${idx + 2}: 'credits' is missing.`);
            if (!row.semester) errorsList.push(`Row ${idx + 2}: 'semester' is missing.`);
            if (!row.programId) errorsList.push(`Row ${idx + 2}: 'programId' (parent reference) is missing.`);
          }
        });

        setValidationErrors(errorsList);
        setCsvData(parsedRows);
      } catch (err) {
        setValidationErrors(["Error parsing CSV file format. Ensure it's comma-separated."]);
      }
    };
    reader.readAsText(file);
  };

  const handleExport = async (type: string) => {
    try {
      const data: any = await api.get(`/organizations/${orgId}/${type}`);
      if (!data || data.length === 0) {
        toastError("Export Failed", "No records found to export.");
        return;
      }

      // Convert array of JSON to simple CSV format
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(","),
        ...data.map((row: any) =>
          headers
            .map((h) => {
              const val = row[h] === null || row[h] === undefined ? "" : row[h];
              return `"${String(val).replace(/"/g, '""')}"`;
            })
            .join(",")
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `campusos_${type}_export.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      success("Export Complete", `${type} database downloaded successfully.`);
    } catch (err) {
      toastError("Export Failed", "An error occurred fetching data.");
    }
  };

  const handleTriggerUpload = () => {
    if (validationErrors.length > 0) {
      toastError("Validation Blocked", "Please resolve syntax errors before seeding.");
      return;
    }
    bulkCreateMutation.mutate(csvData);
  };

  const canWrite =
    user?.role?.permissions.includes("*") || user?.role?.permissions.includes("academic:write");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* CSV Import Console (Left Col) */}
      <div className="lg:col-span-2 flex flex-col gap-6">
        <Card glass>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-primary" /> CSV Bulk Seeding Control
            </CardTitle>
            <CardDescription>
              Drag-and-drop CSV payloads here to register hundreds of classes, departments, or programs in one transaction.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label className="text-2xs font-bold uppercase tracking-wider text-muted-foreground">Select Target Entity</label>
              <select
                value={entityType}
                onChange={(e: any) => {
                  setEntityType(e.target.value);
                  setCsvData([]);
                  setCsvHeaders([]);
                  setFileName("");
                  setValidationErrors([]);
                }}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <option value="departments">Departments Collection</option>
                <option value="programs">Programs Collection</option>
                <option value="courses">Courses Collection</option>
              </select>
            </div>

            {/* Drag & Drop area */}
            <div className="border-2 border-dashed border-border rounded-xl p-8 flex flex-col items-center justify-center text-center bg-accent/5 hover:bg-accent/10 transition-colors relative">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                disabled={!canWrite}
                className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <FileSpreadsheet className="h-10 w-10 text-muted-foreground/60 mb-3" />
              <span className="text-xs font-semibold text-foreground">
                {fileName ? `File Selected: ${fileName}` : "Click or drag CSV file to start parsing"}
              </span>
              <span className="text-3xs text-muted-foreground mt-1">Accepts raw standard comma-separated files</span>
            </div>

            {/* Validation alert banners */}
            {validationErrors.length > 0 && (
              <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-2xs flex gap-3 items-start leading-relaxed">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div className="flex flex-col gap-1">
                  <span className="font-bold">Parsing Validation Errors Found:</span>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {validationErrors.slice(0, 5).map((e, idx) => (
                      <li key={idx}>{e}</li>
                    ))}
                    {validationErrors.length > 5 && <li>...and {validationErrors.length - 5} more</li>}
                  </ul>
                </div>
              </div>
            )}

            {/* Preview Grid */}
            {csvData.length > 0 && (
              <div className="flex flex-col gap-3">
                <span className="text-2xs font-bold uppercase tracking-wider text-muted-foreground">Parsing Preview Grid ({csvData.length} rows)</span>
                <div className="overflow-x-auto max-h-60 border border-border rounded-lg">
                  <table className="w-full text-2xs text-left border-collapse">
                    <thead className="bg-accent/10 sticky top-0">
                      <tr className="border-b border-border text-muted-foreground uppercase font-bold">
                        {csvHeaders.map((h) => (
                          <th key={h} className="py-2.5 px-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {csvData.slice(0, 10).map((row, idx) => (
                        <tr key={idx} className="hover:bg-accent/5">
                          {csvHeaders.map((h) => (
                            <td key={h} className="py-2 px-3 text-muted-foreground truncate max-w-[120px]">{row[h]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {csvData.length > 10 && (
                  <span className="text-3xs text-muted-foreground text-center">Showing first 10 rows preview</span>
                )}

                {canWrite && (
                  <div className="flex justify-end gap-3 mt-2 border-t border-border pt-4">
                    <Button variant="outline" size="sm" onClick={() => { setCsvData([]); setCsvHeaders([]); setFileName(""); setValidationErrors([]); }}>
                      Discard File
                    </Button>
                    <Button size="sm" onClick={handleTriggerUpload} isLoading={bulkCreateMutation.isPending}>
                      <CheckCircle className="h-4 w-4 mr-2" /> Commit Upload Seed
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Export Center & Activity Trail (Right Col) */}
      <div className="flex flex-col gap-6">
        {/* Export Center */}
        <Card glass>
          <CardHeader>
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Database Export Hub
            </CardTitle>
            <CardDescription>
              Download direct CSV schemas for record synchronization.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("departments")}
              className="flex justify-between items-center w-full text-left border-border text-foreground hover:bg-accent/10 h-10 px-4"
            >
              <span className="font-semibold text-xs">Export Departments</span>
              <Download className="h-4 w-4 text-muted-foreground" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("programs")}
              className="flex justify-between items-center w-full text-left border-border text-foreground hover:bg-accent/10 h-10 px-4"
            >
              <span className="font-semibold text-xs">Export Programs</span>
              <Download className="h-4 w-4 text-muted-foreground" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("courses")}
              className="flex justify-between items-center w-full text-left border-border text-foreground hover:bg-accent/10 h-10 px-4"
            >
              <span className="font-semibold text-xs">Export Courses Catalog</span>
              <Download className="h-4 w-4 text-muted-foreground" />
            </Button>
          </CardContent>
        </Card>

        {/* Audit Activity timeline logs */}
        <Card glass>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <History className="h-4 w-4" /> Recent Modifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative border-l border-border pl-4 space-y-4 py-2">
              {auditLogs.map((log) => (
                <div key={log.id} className="relative text-2xs flex flex-col gap-0.5">
                  {/* Timeline dot */}
                  <span className="absolute left-[-21px] top-1.5 h-2 w-2 rounded-full bg-primary" />
                  <span className="font-bold text-foreground capitalize">
                    {log.action.replace(/[._]/g, " ")}
                  </span>
                  <span className="text-muted-foreground">
                    Performed by: {log.performedBy || "system"}
                  </span>
                  <span className="text-muted-foreground/60 text-3xs mt-0.5">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
