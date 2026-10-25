'use client';

import React, { useState, useEffect } from 'react';
import { RefreshCw, ImageOff } from 'lucide-react';
import { monitoringApi } from '@/lib/api/monitoring';

interface SecureSnapshotImageProps {
  snapshotId: number;
  alt: string;
  className?: string;
  isAnnotated?: boolean;
  observationId?: number | null;
  evidenceType?: string;
  onClick?: () => void;
}

export function SecureSnapshotImage({
  snapshotId,
  alt,
  className = '',
  isAnnotated = false,
  observationId,
  evidenceType,
  onClick,
}: SecureSnapshotImageProps) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setLoading(true);
    setError(false);

    const fetchImage = async () => {
      try {
        let blob: Blob;
        if (isAnnotated && observationId) {
          if (evidenceType === 'INFRASTRUCTURE_SNAPSHOT') {
            blob = await monitoringApi.fetchAnnotatedInfrastructureImageBlob(observationId);
          } else {
            blob = await monitoringApi.fetchAnnotatedObservationImageBlob(observationId);
          }
        } else {
          blob = await monitoringApi.fetchSnapshotImageBlob(snapshotId);
        }

        if (!active) return;
        url = URL.createObjectURL(blob);
        setImgUrl(url);
      } catch {
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchImage();

    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [snapshotId, isAnnotated, observationId, evidenceType]);

  if (loading) {
    return (
      <div
        className={`bg-slate-900 border border-slate-800 animate-pulse flex items-center justify-center text-slate-500 ${className}`}
      >
        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (error || !imgUrl) {
    return (
      <div
        className={`bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-600 ${className}`}
      >
        <ImageOff className="w-5 h-5" />
      </div>
    );
  }

  return (
    <img
      src={imgUrl}
      alt={alt}
      className={`${className} cursor-pointer`}
      onClick={onClick}
      loading="lazy"
    />
  );
}
