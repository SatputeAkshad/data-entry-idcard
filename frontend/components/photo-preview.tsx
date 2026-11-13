'use client';
import { useEffect, useRef } from 'react';
import { asset } from '@/lib/api';
type Crop = {
    rotation: number;
    left: number;
    top: number;
    right: number;
    bottom: number;
};
export function PhotoPreview({ path, crop }: {
    path: string;
    crop: Crop;
}) {
    const ref = useRef<HTMLCanvasElement>(null);
    useEffect(() => { let cancelled = false; const img = new Image(); img.onload = () => { if (cancelled || !ref.current)
        return; const rotated = document.createElement('canvas'); const swap = crop.rotation === 90 || crop.rotation === 270; rotated.width = swap ? img.naturalHeight : img.naturalWidth; rotated.height = swap ? img.naturalWidth : img.naturalHeight; const ctx = rotated.getContext('2d'); if (!ctx)
        return; ctx.translate(rotated.width / 2, rotated.height / 2); ctx.rotate(crop.rotation * Math.PI / 180); ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2); const w = (crop.right - crop.left) * rotated.width, h = (crop.bottom - crop.top) * rotated.height; if (w <= 0 || h <= 0)
        return; const scale = Math.min(600 / w, 600 / h, 1); ref.current.width = w * scale; ref.current.height = h * scale; ref.current.getContext('2d')?.drawImage(rotated, crop.left * rotated.width, crop.top * rotated.height, w, h, 0, 0, ref.current.width, ref.current.height); }; img.src = asset(path); return () => { cancelled = true; }; }, [path, crop.rotation, crop.left, crop.top, crop.right, crop.bottom]);
    return <canvas ref={ref} aria-label="Photograph with current crop and rotation" role="img" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}/>;
}
