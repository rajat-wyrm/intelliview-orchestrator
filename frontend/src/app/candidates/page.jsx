"use client";
import { useState, useMemo } from "react";
import { endpoints } from "@/lib/api";
import useSWR from "swr";
import {
  UserCircle,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Download,
} from "lucide-react";
import Card from "@/components/Card";
import StatsCards from "@/components/StatsCards";
import { StatusBadge, Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { SearchInput } from "@/components/SearchInput";
import Pipeline from "@/components/Pipeline";
import { formatDate, riskColor, cn } from "@/lib/utils";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { exportCandidatesCSV } from "@/lib/export";
import { toast } from "@/lib/toast";

// ---------------------------------------------------------------------------
// Task 2.4 — Bulk Candidate Import helpers (CSV parsing + validation)
// ---------------------------------------------------------------------------

const REQUIRED_HEADERS = ["name", "email", "position", "phone"];
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^[+]?[\d\s()-]{7,20}$/;

/** Splits a single CSV line into cells, respecting simple double-quoted fields. */
function parseCSVLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

function isValidPhone(phone) {
  if (!PHONE_REGEX.test(phone)) return false;
  const digitCount = (phone.match(/\d/g) || []).length;
  return digitCount >= 7 && digitCount <= 15;
}

/**
 * Parses raw CSV text into { valid, errors }.
 * - Ignores completely empty lines.
 * - Validates required headers (order-independent).
 * - Validates every row and collects ALL errors (not just the first).
 */
function parseCandidateCSV(csvText) {
  const lines = csvText.split(/\r\n|\n|\r/);

  let headerIndex = 0;
  while (headerIndex < lines.length && lines[headerIndex].trim() === "") {
    headerIndex++;
  }

  if (headerIndex >= lines.length) {
    return { valid: [], errors: ["The CSV file is empty."], headerError: true };
  }

  const headerCells = parseCSVLine(lines[headerIndex]).map((h) =>
    h.trim().toLowerCase()
  );
  const missingHeaders = REQUIRED_HEADERS.filter(
    (h) => !headerCells.includes(h)
  );

  if (missingHeaders.length > 0) {
    return {
      valid: [],
      errors: [
        `Missing required column(s): ${missingHeaders.join(
          ", "
        )}. Expected headers: name, email, position, phone.`,
      ],
      headerError: true,
    };
  }

  const colIndex = {
    name: headerCells.indexOf("name"),
    email: headerCells.indexOf("email"),
    position: headerCells.indexOf("position"),
    phone: headerCells.indexOf("phone"),
  };

  const errors = [];
  const valid = [];

  for (let i = headerIndex + 1; i < lines.length; i++) {
    const rawLine = lines[i];
    if (rawLine.trim() === "") continue; // ignore completely empty lines

    const rowNumber = i + 1; // matches the row number if opened in a spreadsheet
    const cells = parseCSVLine(rawLine);

    const candidate = {
      name: (cells[colIndex.name] || "").trim(),
      email: (cells[colIndex.email] || "").trim(),
      position: (cells[colIndex.position] || "").trim(),
      phone: (cells[colIndex.phone] || "").trim(),
    };

    const rowErrors = [];
    if (!candidate.name) rowErrors.push("Name is required");
    if (!candidate.email) rowErrors.push("Email is required");
    else if (!EMAIL_REGEX.test(candidate.email)) rowErrors.push("Email is invalid");
    if (!candidate.position) rowErrors.push("Position is required");
    if (!candidate.phone) rowErrors.push("Phone is required");
    else if (!isValidPhone(candidate.phone)) rowErrors.push("Phone is invalid");

    if (rowErrors.length > 0) {
      errors.push(`Row ${rowNumber}: ${rowErrors.join(", ")}`);
    } else {
      valid.push(candidate);
    }
  }

  return { valid, errors, headerError: false };
}

function useCandidateData(search, skill, position, dateFrom, dateTo, page) {
  const params = new URLSearchParams();

  if (search.trim()) {
    params.set("search", search.trim());
  }

  if (skill.trim()) {
    params.set("skill", skill.trim());
  }

  if (position.trim()) {
    params.set("position", position.trim());
  }

  if (dateFrom) {
    params.set("date_from", dateFrom);
  }

  if (dateTo) {
    params.set("date_to", dateTo);
  }

  params.set("page", page.toString());

  const url = `/candidates?${params.toString()}`;

  const { data, error, isLoading, mutate } = useSWR(url);

  return {
    candidates: data?.candidates ?? [],
    count: data?.count ?? 0,
    limit: data?.limit ?? 20,
    page: data?.page ?? page,
    isLoading,
    error,
    mutate,
  };
}

export default function CandidatesPage() {
  const [search, setSearch] = useState("");
  const [skill, setSkill] = useState("");
  const [position, setPosition] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState(null);

  const { candidates, count, limit, isLoading, error, mutate } =
    useCandidateData(search, skill, position, dateFrom, dateTo, page);

  // --- Task 2.4: Bulk Candidate Import state ------------------------------
  const [csvErrors, setCsvErrors] = useState([]);
  const [csvSummary, setCsvSummary] = useState(null); // { valid, invalid }
  const [validCandidates, setValidCandidates] = useState([]);
  const [importStatus, setImportStatus] = useState("idle"); // idle | importing | success | error
  const [importMessage, setImportMessage] = useState("");
  const [importErrors, setImportErrors] = useState([]); // backend-reported per-row failures

  const resetFileInput = () => {
    const el = document.getElementById("csvFile");
    if (el) el.value = "";
  };

  const handleCsvFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Reset previous import state for a fresh run
    setCsvErrors([]);
    setCsvSummary(null);
    setValidCandidates([]);
    setImportStatus("idle");
    setImportMessage("");
    setImportErrors([]);

    const reader = new FileReader();

    reader.onload = (event) => {
      const csvText = event.target.result;
      const { valid, errors, headerError } = parseCandidateCSV(csvText);

      if (headerError) {
        setCsvErrors(errors);
        resetFileInput();
        return;
      }

      setCsvErrors(errors);
      setValidCandidates(valid);
      setCsvSummary({ valid: valid.length, invalid: errors.length });
    };

    reader.onerror = () => {
      setCsvErrors(["Unable to read the file."]);
      resetFileInput();
    };

    reader.readAsText(file);
  };

  const handleBulkImport = async () => {
    if (validCandidates.length === 0) return;

    setImportStatus("importing");
    setImportMessage("");
    setImportErrors([]);

    try {
      const data = await endpoints.bulkCreateCandidates({ candidates: validCandidates });

      const importedCount = data?.imported ?? validCandidates.length;
      const failedRows = data?.errors ?? [];

      setImportStatus("success");
      setImportErrors(failedRows);

      if (failedRows.length > 0) {
        setImportMessage(
          `Imported ${importedCount} candidate${importedCount !== 1 ? "s" : ""}. ${failedRows.length} row${failedRows.length !== 1 ? "s" : ""} failed on the server (see below).`
        );
      } else {
        setImportMessage(
          `Successfully imported ${importedCount} candidate${importedCount !== 1 ? "s" : ""}.`
        );
      }

      setValidCandidates([]);
      setCsvErrors([]);
      setCsvSummary(null);
      resetFileInput();
      mutate();
    } catch (err) {
      setImportStatus("error");
      setImportMessage(err.message || "Failed to import candidates. Please try again.");
    }
  };

  const filtered = candidates;

  const selected = candidates.find((c) => c.candidate_id === selectedId);

  const handleExportCSV = () => {
    if (candidates.length === 0) {
      toast.error("No candidates to export");
      return;
    }
    try {
      exportCandidatesCSV(candidates);
      toast.success("CSV exported successfully");
    } catch (error) {
      toast.error("Failed to export CSV");
    }
  };

  const statusData = useMemo(() => {
    if (!selected) return [];
    const counts = {};
    for (const s of selected.sessions) {
      counts[s.status] = (counts[s.status] || 0) + 1;
    }
    return Object.entries(counts).map(([status, count]) => ({ status, count }));
  }, [selected]);

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-50">Candidates</h1>
            <p className="text-sm text-muted">
              Candidate profiles, interview history, and performance analytics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 hover:bg-bg-panel transition-colors"
            >
              <Download size={16} />
              Export CSV
            </button>

            <input
              type="file"
              id="csvFile"
              accept=".csv"
              style={{ display: "none" }}
              onChange={handleCsvFileChange}
            />

            <button
              onClick={() => document.getElementById("csvFile").click()}
              disabled={importStatus === "importing"}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Import CSV
            </button>

            <div className="text-xs text-muted">{candidates.length} candidates</div>
          </div>
        </div>

        <CandidateRegistrationForm onRegistered={mutate} />

        {(csvSummary || importStatus !== "idle") && (
          <Card title="Bulk Import" description="CSV validation results">
            <div className="space-y-3">
              {csvSummary && (
                <div className="flex flex-wrap items-center gap-4 text-sm">
                  <span className="font-medium text-emerald-400">
                    Valid rows: {csvSummary.valid}
                  </span>
                  <span className="font-medium text-rose-400">
                    Invalid rows: {csvSummary.invalid}
                  </span>
                </div>
              )}

              {csvErrors.length > 0 && (
                <div className="max-h-48 overflow-y-auto rounded-md border border-rose-900/40 bg-rose-950/20 p-3">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-rose-400">
                    <AlertTriangle size={13} />
                    {csvErrors.length} row{csvErrors.length !== 1 ? "s" : ""} skipped
                  </div>
                  <ul className="space-y-0.5 text-xs text-rose-300/90">
                    {csvErrors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {importStatus === "success" && (
                <div className="flex items-center gap-1.5 rounded-md border border-emerald-900/40 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-400">
                  <CheckCircle2 size={14} />
                  {importMessage}
                </div>
              )}

              {importStatus === "error" && (
                <div className="flex items-center gap-1.5 rounded-md border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-xs text-rose-400">
                  <XCircle size={14} />
                  {importMessage}
                </div>
              )}

              {importErrors.length > 0 && (
                <div className="max-h-48 overflow-y-auto rounded-md border border-amber-900/40 bg-amber-950/20 p-3">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-amber-400">
                    <AlertTriangle size={13} />
                    {importErrors.length} row{importErrors.length !== 1 ? "s" : ""} failed on the server
                  </div>
                  <ul className="space-y-0.5 text-xs text-amber-300/90">
                    {importErrors.map((e, idx) => (
                      <li key={idx}>
                        {e.email ? `${e.email}: ` : ""}{e.error || "Unknown error"}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {validCandidates.length > 0 && importStatus !== "success" && (
                <button
                  onClick={handleBulkImport}
                  disabled={importStatus === "importing"}
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {importStatus === "importing"
                    ? "Importing..."
                    : `Import ${validCandidates.length} candidate${validCandidates.length !== 1 ? "s" : ""}`}
                </button>
              )}
            </div>
          </Card>
        )}

        <StatsCards
          data={{
            totalCandidates: candidates.length,
            pendingReview: candidates.reduce((a, c) => a + c.active_sessions, 0),
            completed: candidates.reduce((a, c) => a + c.completed_sessions, 0),
            activeNow: candidates.filter((c) => c.active_sessions > 0).length,
          }}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <Card
              title="Candidate List"
              description={`${count} candidates`}
              action={
                <SearchInput
                  value={search}
                  onChange={(value) => {
                    setSearch(value);
                    setPage(1);
                  }}
                  placeholder="Search name or email..."
                  className="w-48"
                />
              }
            >
              <div className="mb-3 flex flex-wrap gap-2">
                <select
                  value={skill}
                  onChange={(e) => {
                    setSkill(e.target.value);
                    setPage(1);
                  }}
                  className="rounded-md border px-3 py-2"
                >
                  <option value="">All Skills</option>
                  <option value="python">Python</option>
                  <option value="FastAPI">FastAPI</option>
                  <option value="SQL">SQL</option>
                  <option value="Java">Java</option>
                  <option value="React">React</option>
                </select>

                <input
                  type="text"
                  value={position}
                  onChange={(e) => {
                    setPosition(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Position"
                  className="rounded-md border px-3 py-2"
                />

                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => {
                    setDateFrom(e.target.value);
                    setPage(1);
                  }}
                  className="rounded-md border px-3 py-2"
                />

                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => {
                    setDateTo(e.target.value);
                    setPage(1);
                  }}
                  className="rounded-md border px-3 py-2"
                />
              </div>

              {error ? (
                <ErrorState error={error} onRetry={mutate} />
              ) : isLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : candidates.length === 0 ? (
                <EmptyState
                  title="No candidates"
                  description="Candidate data will appear after sessions are completed."
                />
              ) : (
                <>
                  <div className="max-h-[500px] space-y-1 overflow-y-auto">
                    {filtered.map((c) => (
                      <button
                        key={c.candidate_id}
                        onClick={() => setSelectedId(c.candidate_id)}
                        className={cn(
                          "flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                          selectedId === c.candidate_id
                            ? "bg-accent/15 text-accent-light"
                            : "text-zinc-300 hover:bg-bg-card",
                        )}
                      >
                        <div className="min-w-0">
                          <div className="truncate font-mono text-xs text-zinc-200">
                            {c.candidate_id}
                          </div>
                          <div className="text-[10px] text-muted">
                            {c.total_sessions} session
                            {c.total_sessions !== 1 ? "s" : ""}
                          </div>
                        </div>
                        {c.avg_risk_score != null && (
                          <Badge variant={riskColor(c.avg_risk_score)}>
                            {c.avg_risk_score.toFixed(2)}
                          </Badge>
                        )}
                      </button>
                    ))}
                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="rounded-md border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Previous
                    </button>

                    <span className="text-xs text-muted">Page {page}</span>

                    <button
                      type="button"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={candidates.length < limit}
                      className="rounded-md border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </>
              )}
            </Card>
          </div>

          <div className="lg:col-span-2">
            {!selected ? (
              <Card>
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <UserCircle size={48} className="mb-3 text-muted opacity-30" />
                  <p className="text-sm text-zinc-300">
                    Select a candidate to view details
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Click on a candidate from the list to see their profile
                  </p>
                </div>
              </Card>
            ) : (
              <div className="space-y-4">
                <Card
                  title={selected.candidate_id}
                  description="Candidate profile and performance"
                >
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-muted">
                        Total
                      </div>
                      <div className="mt-1 text-lg font-semibold text-zinc-50">
                        {selected.total_sessions}
                      </div>
                    </div>
                    <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-muted">
                        Completed
                      </div>
                      <div className="mt-1 text-lg font-semibold text-emerald-400">
                        {selected.completed_sessions}
                      </div>
                    </div>
                    <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-muted">
                        Failed
                      </div>
                      <div className="mt-1 text-lg font-semibold text-rose-400">
                        {selected.failed_sessions}
                      </div>
                    </div>
                    <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-muted">
                        Avg Risk
                      </div>
                      <div className="mt-1 text-lg font-semibold text-zinc-50">
                        {selected.avg_risk_score != null
                          ? selected.avg_risk_score.toFixed(3)
                          : "—"}
                      </div>
                    </div>
                  </div>
                </Card>

                {statusData.length > 0 && (
                  <Card title="Session Status Distribution">
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={statusData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="status" stroke="#71717a" fontSize={11} />
                        <YAxis stroke="#71717a" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            background: "#12121a",
                            border: "1px solid #27272a",
                            borderRadius: 8,
                          }}
                        />
                        <Bar
                          dataKey="count"
                          fill="#6366f1"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                )}

                <Card
                  title="Interview History"
                  description="All sessions for this candidate"
                >
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-left text-xs uppercase tracking-wide text-muted">
                        <tr>
                          <th className="py-2 pr-4">Session</th>
                          <th className="py-2 pr-4">Pipeline</th>
                          <th className="py-2 pr-4">Status</th>
                          <th className="py-2 pr-4">Risk</th>
                          <th className="py-2 pr-4">Worker</th>
                          <th className="py-2 pr-4">Updated</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.sessions
                          .sort(
                            (a, b) =>
                              new Date(b.updated_at || 0) -
                              new Date(a.updated_at || 0),
                          )
                          .map((s) => (
                            <tr
                              key={s.session_id}
                              className="border-t border-border"
                            >
                              <td className="py-2 pr-4 font-mono text-xs text-zinc-300">
                                {s.session_id}
                              </td>
                              <td className="py-2 pr-4">
                                <Pipeline current={s.status} />
                              </td>
                              <td className="py-2 pr-4">
                                <StatusBadge status={s.status} />
                              </td>
                              <td className="py-2 pr-4">
                                {s.risk_score != null ? (
                                  <Badge variant={riskColor(s.risk_score)}>
                                    {s.risk_score.toFixed(2)}
                                  </Badge>
                                ) : (
                                  <span className="text-muted">—</span>
                                )}
                              </td>
                              <td className="py-2 pr-4 font-mono text-xs text-muted">
                                {s.assigned_node ?? "—"}
                              </td>
                              <td className="py-2 pr-4 text-muted">
                                {formatDate(s.updated_at ?? s.end_time)}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}

function CandidateRegistrationForm({ onRegistered }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [skills, setSkills] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const submit = async (event) => {
    event.preventDefault();

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const candidate = await endpoints.createCandidate({
        name: name.trim(),
        email: email.trim(),
        resume_text: resumeText.trim() || null,
        skills: skills
          .split(",")
          .map((skill) => skill.trim())
          .filter(Boolean),
      });

      setSuccess(
        `Candidate ${candidate.candidate_id ?? candidate.name ?? name.trim()} registered successfully.`
      );

      setName("");
      setEmail("");
      setResumeText("");
      setSkills("");

      onRegistered?.(candidate);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to register candidate"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card
      title="Candidate Registration"
      description="Create a new candidate profile."
    >
      <form
        onSubmit={submit}
        noValidate={false}
        className="space-y-4"
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label
              htmlFor="candidate-name"
              className="block text-xs font-medium text-muted"
            >
              Name
            </label>

            <input
              id="candidate-name"
              name="name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              minLength={1}
              maxLength={200}
              placeholder="Jane Doe"
              className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label
              htmlFor="candidate-email"
              className="block text-xs font-medium text-muted"
            >
              Email
            </label>

            <input
              id="candidate-email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              maxLength={255}
              placeholder="jane@example.com"
              className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="candidate-resume"
            className="block text-xs font-medium text-muted"
          >
            Resume
          </label>

          <textarea
            id="candidate-resume"
            name="resume"
            value={resumeText}
            onChange={(event) => setResumeText(event.target.value)}
            rows={4}
            placeholder="Candidate resume information..."
            className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>

        <div>
          <label
            htmlFor="candidate-skills"
            className="block text-xs font-medium text-muted"
          >
            Skills
          </label>

          <input
            id="candidate-skills"
            name="skills"
            type="text"
            value={skills}
            onChange={(event) => setSkills(event.target.value)}
            placeholder="Java, Python, React"
            className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
          />

          <p className="mt-1 text-[10px] text-muted">
            Enter skills separated by commas.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-400"
          >
            {error}
          </div>
        )}

        {success && (
          <div
            role="status"
            className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400"
          >
            {success}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Registering..." : "Register Candidate"}
          </button>
        </div>
      </form>
    </Card>
  );
}
