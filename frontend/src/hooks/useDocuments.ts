import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { DocumentRecord } from "../api/types";

export function useDocuments(applicationId: string | undefined, token: string | null) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    if (!applicationId || !token) return;
    setLoading(true);
    try {
      const res = await api.listDocuments(applicationId, token);
      setDocuments(res.items);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const uploadDocument = useCallback(
    async (file: File, documentType: string) => {
      if (!applicationId || !token) throw new Error("Missing application session");
      setUploading(true);
      setError(null);
      try {
        const res = await api.uploadDocument(applicationId, token, file, documentType);
        await fetchDocuments();
        return res;
      } catch (err: unknown) {
        setError(errorMessage(err) || "Failed to upload document");
        throw err;
      } finally {
        setUploading(false);
      }
    },
    [applicationId, token, fetchDocuments],
  );

  const deleteDocument = useCallback(
    async (documentId: string) => {
      if (!token) throw new Error("Missing authorization token");
      setLoading(true);
      setError(null);
      try {
        const res = await api.deleteDocument(documentId, token);
        await fetchDocuments();
        return res;
      } catch (err: unknown) {
        setError(errorMessage(err) || "Failed to delete document");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [token, fetchDocuments],
  );

  return {
    documents,
    loading,
    uploading,
    error,
    refresh: fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
}

