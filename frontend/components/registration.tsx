'use client';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import { Camera, Check, RotateCcw, Save, ArrowRight, Upload, Crop as CropIcon } from 'lucide-react';
import { Button } from './ui/button';
import { PhotoPreview } from './photo-preview';
import { api, asset, type Institution, type Student, type Capture } from '@/lib/api';
export function Registration({ institution, existing, onSaved, onNext }: {
    institution: Institution;
    existing: Student | null;
    onSaved: () => void;
    onNext: () => void;
}) {
    const schema = z.object(Object.fromEntries(institution.fields.map(f => [f.key, f.required ? z.string().trim().min(1, `${f.label} is required`) : z.string()])));
    const form = useForm<Record<string, string>>({ resolver: zodResolver(schema), defaultValues: existing?.data || Object.fromEntries(institution.fields.map(f => [f.key, ''])) });
    const [student, setStudent] = useState<Student | null>(existing), [capture, setCapture] = useState<Capture | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState(''), [cropOpen, setCropOpen] = useState(false);
    const [crop, setCrop] = useState({ rotation: 0, left: 0, top: 0, right: 1, bottom: 1 });
    const inbox = useQuery({ queryKey: ['inbox'], queryFn: () => api<any[]>('/inbox'), refetchInterval: 3000 });
    useEffect(() => { if (existing?.photo_id)
        api<Capture>('/captures/' + existing.photo_id).then(setCapture).catch(e => setError(e.message)); }, [existing?.photo_id]);
    const run = async (fn: () => Promise<void>) => { setBusy(true); setError(''); setMessage(''); try {
        await fn();
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } };
    const ensureStudent = async () => { if (student)
        return student; const s = await api<Student>('/students', { method: 'POST', body: JSON.stringify({ institution_id: institution.id, data: form.getValues(), status: 'draft' }) }); setStudent(s); return s; };
    const start = () => run(async () => { const s = await ensureStudent(); const c = await api<Capture>(`/students/${s.id}/capture`, { method: 'POST' }); setCapture(c); setCrop({ rotation: 0, left: 0, top: 0, right: 1, bottom: 1 }); setMessage('Session opened. Trigger your camera in Nikon software, then select the matching received image below, or import a photo.'); });
    const upload = (file?: File) => { if (!file)
        return; void run(async () => { let c = capture; if (!c || c.state !== 'Waiting for Image') {
        const s = await ensureStudent();
        c = await api<Capture>(`/students/${s.id}/capture`, { method: 'POST' });
        setCapture(c);
    } const body = new FormData(); body.append('file', file); setCapture(await api<Capture>(`/captures/${c.id}/image`, { method: 'POST', body })); setCrop({ rotation: 0, left: 0, top: 0, right: 1, bottom: 1 }); }); };
    const save = (next: boolean, draft = false) => run(async () => { if (!draft && !await form.trigger())
        return; const s = await ensureStudent(); const updated = await api<Student>('/students/' + s.id, { method: 'PUT', body: JSON.stringify({ institution_id: institution.id, data: form.getValues(), status: draft ? 'draft' : 'ready', revision: s.revision }) }); setStudent(updated); onSaved(); setMessage(draft ? 'Draft saved.' : 'Student saved with approved photograph.'); if (next) {
        const repeated = Object.fromEntries(institution.fields.map(f => [f.key, f.repeat ? form.getValues(f.key) : '']));
        setCapture(null);
        setStudent(null);
        setCropOpen(false);
        form.reset(repeated);
        onNext();
    } });
    const photo = capture?.approved || capture?.original;
    return <><div className="heading"><div><div className="eyebrow">REGISTRATION DESK</div><h1>{existing ? 'Student photography' : 'New student'}</h1><p className="muted">{institution.name} · {institution.year}</p></div><span className="badge">{student ? 'Draft linked to student' : 'New registration'}</span></div>{error && <div role="alert" className="error">{error}</div>}{message && <div role="status" className="notice">{message}</div>}<div className="grid two">
 <section className="card"><h2><span className="step">1</span>Student details</h2><p className="muted">Fields marked * are required when saving a student.</p><div className="divider"/><form onSubmit={e => { e.preventDefault(); void save(false); }}><div className="fields">{institution.fields.map(f => <label className="field" key={f.key}>{f.label}{f.required ? ' *' : ''}{f.type === 'select' ? <select {...form.register(f.key)}><option value="">Select {f.label.toLowerCase()}</option>{f.options?.map(v => <option key={v}>{v}</option>)}</select> : <input type={f.type === 'date' ? 'date' : 'text'} autoComplete="off" {...form.register(f.key)}/>}<span className="help">{form.formState.errors[f.key]?.message as string}{f.repeat ? ' Kept for the next student.' : ''}</span></label>)}</div><div className="divider"/><div className="actions"><Button type="button" variant="outline" disabled={busy} onClick={() => save(false, true)}><Save size={15}/>Save Draft</Button><Button type="submit" disabled={busy || capture?.state !== 'Approved'}>Save Student</Button><Button type="button" disabled={busy || capture?.state !== 'Approved'} onClick={() => save(true)}>Save & Next<ArrowRight size={15}/></Button></div></form></section>
 <section className="card"><div className="actions" style={{ justifyContent: 'space-between' }}><h2><span className="step">2</span>Student photograph</h2><span className={'badge ' + (capture?.state === 'Approved' ? '' : 'pending')}>{capture?.state || 'No photo'}</span></div><p className="muted">Nikon tethered folder / manual import</p><div className="photo-stage">{photo ? <PhotoPreview path={photo} crop={capture?.state === 'Reviewing' ? crop : { rotation: 0, left: 0, top: 0, right: 1, bottom: 1 }}/> : <><Camera /><span className="photo-caption">Start a capture session or import a photograph. Each student receives a separate photo session.</span></>}</div><div className="actions"><Button disabled={busy || capture?.state === 'Reviewing'} onClick={start}><Camera size={16}/>Capture Photo</Button><label className="button outline" style={{ cursor: busy ? 'wait' : 'pointer' }}><Upload size={16}/>Import Photo<input hidden type="file" accept="image/jpeg,image/png" disabled={busy} onChange={e => { upload(e.target.files?.[0]); e.target.value = ''; }}/></label></div><p className="help">Capture Photo arms reception. Use the camera shutter or Nikon software; integrated shutter and live view are not enabled.</p>
 {capture?.state === 'Reviewing' && <><div className="divider"/><div className="actions"><Button disabled={busy} onClick={() => run(async () => { const r = await api<{
        capture: Capture;
        student: Student;
    }>(`/captures/${capture.id}/approve`, { method: 'POST', body: JSON.stringify(crop) }); setCapture(r.capture); setStudent(r.student); setCropOpen(false); })}><Check size={16}/>Accept Photo</Button><Button variant="outline" disabled={busy} onClick={() => run(async () => { setCapture(await api<Capture>(`/captures/${capture.id}/retake`, { method: 'POST' })); setCropOpen(false); setCrop({ rotation: 0, left: 0, top: 0, right: 1, bottom: 1 }); })}><RotateCcw size={16}/>Retake</Button><Button variant="ghost" onClick={() => setCropOpen(!cropOpen)}><CropIcon size={16}/>Crop / Adjust</Button></div>{cropOpen && <><p className="help">The preview shows the crop that will be approved. Adjust boundaries to reposition; the original is retained.</p><div className="crop-grid"><label className="field">Zoom<input type="range" min="1" max="4" step="0.05" value={1 / (crop.right - crop.left)} onChange={e => { const span = 1 / +e.target.value; setCrop({ ...crop, left: (1 - span) / 2, right: (1 + span) / 2, top: (1 - span) / 2, bottom: (1 + span) / 2 }); }}/></label><label className="field">Rotation<select value={crop.rotation} onChange={e => setCrop({ ...crop, rotation: +e.target.value })}>{[0, 90, 180, 270].map(v => <option key={v} value={v}>{v}°</option>)}</select></label>{(['left', 'top', 'right', 'bottom'] as const).map(k => <label className="field" key={k}>{k} ({Math.round(crop[k] * 100)}%)<input type="range" min="0" max="100" value={crop[k] * 100} onChange={e => setCrop({ ...crop, [k]: +e.target.value / 100 })}/></label>)}</div></>}</>}
 {capture?.state === 'Waiting for Image' && <><div className="divider"/><h3>Received photos — select this student’s image</h3><p className="help">Confirm the face before accepting. Delayed files remain unassigned.</p><div className="inbox">{inbox.data?.map(item => <button key={item.id} disabled={busy} onClick={() => run(async () => setCapture(await api<Capture>(`/captures/${capture.id}/inbox/${item.id}`, { method: 'POST' })))}><img src={asset(item.path)} alt={item.source_name}/>{item.source_name}<br />{new Date(item.received * 1000).toLocaleTimeString()}</button>)}</div>{!inbox.data?.length && <p className="empty">Waiting for photographs in the configured tether folder.</p>}</>}
 </section></div></>;
}
