"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Upload, FileText, CheckCircle2, AlertCircle } from "lucide-react";
import Card from "@/components/Card";
import { endpoints } from "@/lib/api";

export default function CandidateProfilePage() {
  const params = useParams();
  const candidateId = params?.id;

  const [selectedFile, setSelectedFile] = useState(null);
  const [parsedResume, setParsedResume] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setError("");
    setParsedResume(null);

    if (file.type !== "application/pdf") {
      setSelectedFile(null);
      setError("Please select a PDF file.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setSelectedFile(null);
      setError("PDF must be smaller than 5 MB.");
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError("Please select a PDF file first.");
      return;
    }

    setUploading(true);
    setError("");
    setParsedResume(null);

    try {
      const result = await endpoints.parseResume(selectedFile);

      setParsedResume(result);
    } catch (err) {
      setError(err?.message || "Failed to parse resume.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/candidates"
          className="rounded-md p-2 text-muted hover:bg-bg-card hover:text-zinc-100"
        >
          <ArrowLeft size={18} />
        </Link>

        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            Candidate Profile
          </h1>

          <p className="text-sm text-muted">
            Candidate ID: {candidateId}
          </p>
        </div>
      </div>

      {/* Resume Upload */}
      <Card
        title="Resume"
        description="Upload a PDF resume to automatically extract skills."
      >
        <div className="space-y-4">
          {/* File selector */}
          <label
            htmlFor="resume-upload"
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-bg-card px-6 py-10 text-center transition hover:border-accent"
          >
            <Upload size={32} className="mb-3 text-muted" />

            <span className="text-sm font-medium text-zinc-200">
              Choose a resume PDF
            </span>

            <span className="mt-1 text-xs text-muted">
              PDF files only, maximum 5 MB
            </span>

            <input
              id="resume-upload"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>

          {/* Selected file */}
          {selectedFile && (
            <div className="flex items-center gap-3 rounded-md border border-border bg-bg-card p-3">
              <FileText size={20} className="text-accent-light" />

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-zinc-200">
                  {selectedFile.name}
                </p>

                <p className="text-xs text-muted">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Upload button */}
          <button
            type="button"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Parsing resume..." : "Upload & Parse Resume"}
          </button>

          {/* Success */}
          {parsedResume && (
            <div className="flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
              <CheckCircle2 size={18} />
              <span>Resume parsed successfully.</span>
            </div>
          )}
        </div>
      </Card>

      {/* Parsed Skills */}
      {parsedResume && (
        <Card
          title="Skills"
          description="Skills automatically extracted from the resume."
        >
          {parsedResume.skills?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {parsedResume.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent-light"
                >
                  {skill}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">
              No matching skills were found in this resume.
            </p>
          )}
        </Card>
      )}

      {/* Resume text preview */}
      {parsedResume?.resume_text && (
        <Card
          title="Resume Text"
          description="Text extracted from the uploaded PDF."
        >
          <div className="max-h-96 overflow-y-auto rounded-md border border-border bg-bg-card p-4">
            <pre className="whitespace-pre-wrap text-xs leading-5 text-zinc-300">
              {parsedResume.resume_text}
            </pre>
          </div>
        </Card>
      )}
    </div>
  );
}