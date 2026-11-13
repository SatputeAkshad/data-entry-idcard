'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from './ui/button';
import { api, type Institution, type Student, type Template } from '@/lib/api';
export function Records({ institution, onEdit, onProduced }: {
    institution: Institution;
    onEdit: (s: Student) => void;
    onProduced: () => void;
}) {
    const [q, setQ] = useState(''), [status, setStatus] = useState(''), [selected, setSelected] = useState<string[]>([]), [template, setTemplate] = useState(''), [error, setError] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false);
    const query = useQuery({ queryKey: ['students', institution.id, q, status], queryFn: () => api<Student[]>(`/students?institution_id=${institution.id}&q=${encodeURIComponent(q)}&status=${status}`) });
    const templates = useQuery({ queryKey: ['templates', institution.id], queryFn: () => api<Template[]>('/templates?institution_id=' + institution.id) });
    const run = async (fn: () => Promise<void>) => { setBusy(true); setError(''); try {
        await fn();
        await query.refetch();
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } };
    return <><div className="heading"><div><div className="eyebrow">{institution.name}</div><h1>Student records</h1><p className="muted">Import a class list, photograph students, and prepare production.</p></div></div>{error && <div className="error">{error}</div>}{message && <div className="notice">{message}</div>}<section className="card"><div className="toolbar"><input className="input" placeholder="Search student details…" aria-label="Search students" value={q} onChange={e => setQ(e.target.value)}/><select className="input" aria-label="Filter status" value={status} onChange={e => { setStatus(e.target.value); setSelected([]); }}><option value="">All students</option><option value="pending">Photography pending</option>{['draft', 'ready', 'generated', 'printed'].map(s => <option key={s}>{s}</option>)}</select><label className="button outline">Import CSV / Excel<input hidden type="file" accept=".csv,.xlsx" disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file)
        void run(async () => { const body = new FormData(); body.append('file', file); const r = await api<{
            imported: number;
        }>(`/institutions/${institution.id}/import`, { method: 'POST', body }); setMessage(`${r.imported} students imported. Open a student to begin photography.`); }); }}/></label><a href={`/api/institutions/${institution.id}/export?format=csv`}>CSV</a><a href={`/api/institutions/${institution.id}/export?format=xlsx`}>Excel</a></div><p className="help">Import headers: {institution.fields.map(f => f.key).join(', ')}</p><div className="table-wrap"><table><thead><tr><th><input type="checkbox" aria-label="Select all visible students" checked={!!query.data?.length && query.data.every(s => selected.includes(s.id))} onChange={e => setSelected(e.target.checked ? query.data?.map(s => s.id) || [] : [])}/></th><th>Student</th><th>Class / department</th><th>Photograph</th><th>Status</th><th>Actions</th></tr></thead><tbody>{query.data?.map(s => <tr key={s.id}><td><input type="checkbox" aria-label={'Select ' + s.data.full_name} checked={selected.includes(s.id)} onChange={e => setSelected(e.target.checked ? [...selected, s.id] : selected.filter(id => id !== s.id))}/></td><td><strong>{s.data.full_name || 'Unnamed draft'}</strong><small>{s.data.student_id || s.data.roll_number || s.id.slice(0, 8)}</small></td><td>{s.data.class || s.data.department || '—'}</td><td><span className={'badge ' + (s.photo_id ? '' : 'pending')}>{s.photo_id ? 'Approved' : 'Pending'}</span></td><td>{s.status}</td><td><div className="actions"><Button variant="ghost" onClick={() => onEdit(s)}>Open</Button>{s.status === 'generated' && <Button variant="ghost" disabled={busy} onClick={() => run(async () => { await api(`/students/${s.id}/printed`, { method: 'POST' }); })}>Mark printed</Button>}<Button variant="ghost" disabled={busy} onClick={() => { if (window.confirm(`Delete ${s.data.full_name || 'this draft'}? This removes the record.`))
        void run(async () => { await api('/students/' + s.id, { method: 'DELETE' }); setSelected(selected.filter(id => id !== s.id)); }); }}>Delete</Button></div></td></tr>)}</tbody></table></div>{!query.data?.length && <div className="empty">No matching students. Register a student or import a class list.</div>}<div className="divider"/><div className="toolbar"><span>{selected.length} selected</span><select className="input" aria-label="Production template" value={template} onChange={e => setTemplate(e.target.value)}><option value="">Choose a design…</option>{templates.data?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select><Button disabled={busy || !selected.length || !template} onClick={() => run(async () => { await api('/jobs', { method: 'POST', body: JSON.stringify({ key: crypto.randomUUID(), template_id: template, student_ids: selected }) }); onProduced(); })}>Generate Cards</Button><Button variant="outline" onClick={async () => { try {
        const pending = await api<Student[]>('/students?institution_id=' + institution.id + '&status=pending');
        if (pending[0])
            onEdit(pending[0]);
        else
            setMessage('All students have an approved photo.');
    }
    catch (e) {
        setError((e as Error).message);
    } }}>Photograph next student</Button></div></section></>;
}
