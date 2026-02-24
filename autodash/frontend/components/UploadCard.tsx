"use client";

import { useMemo, useState } from "react";
import type { DragEvent } from "react";
import { useRef } from "react";
import { useRouter } from "next/navigation";

import { uploadDataset } from "@/lib/api";

const ALLOWED_TYPES = [
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel"
];

export function UploadCard() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buttonLabel = useMemo(() => {
    if (isUploading) return "Uploading...";
    if (file) return "Upload and Build Dashboard";
    return "Select a Dataset";
  }, [file, isUploading]);

  function validateAndSetFile(candidate: File | null): void {
    if (!candidate) return;
    const extension = candidate.name.split(".").pop()?.toLowerCase();
    const isAllowed =
      ALLOWED_TYPES.includes(candidate.type) ||
      extension === "csv" ||
      extension === "xlsx" ||
      extension === "xls";
    if (!isAllowed) {
      setError("Only CSV and XLSX files are supported.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  }

  async function onUpload(): Promise<void> {
    if (isUploading) return;
    if (!file) {
      fileInputRef.current?.click();
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      const response = await uploadDataset(file);
      router.push(`/dashboard/${response.dataset_id}`);
    } catch (uploadError) {
      const message = uploadError instanceof Error ? uploadError.message : "Upload failed.";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0] ?? null;
    validateAndSetFile(dropped);
  }

  return (
    <div className="upload-card">
      <div className="upload-header">
        <h2>Drop in CSV/XLSX</h2>
        <p>AutoDash profiles your data and creates a dashboard spec automatically.</p>
      </div>

      <label
        className={`dropzone${isDragging ? " dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(event) => validateAndSetFile(event.target.files?.[0] ?? null)}
        />
        <span>{file ? file.name : "Drop file here or click to choose"}</span>
        {file ? (
          <small>
            {(file.size / 1024).toFixed(1)} KB - {file.type || "unknown type"}
          </small>
        ) : (
          <small>Supported: CSV, XLSX, XLS</small>
        )}
      </label>

      <button type="button" onClick={onUpload} disabled={isUploading}>
        {buttonLabel}
      </button>

      {isUploading ? (
        <>
          <p className="status">Processing file and generating metadata...</p>
          <div className="progress-track">
            <div className="progress-fill" />
          </div>
        </>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

