'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from './ui/button';
import { api, asset, type Institution, type Template, type Job } from '@/lib/api';
export function Templates({ institution }: {
    institution: Institution;
}) {
    const query = useQuery({ queryKey: ['templates', institution.id], queryFn: () => api<Template[]>('/templates?institution_id=' + institution.id) });
    const [name, setName] = useState(''), [file, setFile] = useState<File | null>(null), [mapping, setMapping] = useState<Record<string, string>>({ STUDENT_NAME: 'full_name', STUDENT_ID: 'student_id', STUDENT_PHOTO: 'photo' }), [width, setWidth] = useState(85.6), [height, setHeight] = useState(54), [bleed, setBleed] = useState(0), [error, setError] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false);
    async function save() { if (!file)
        return; setBusy(true); setError(''); try {
        const body = new FormData();
        body.append('file', file);
        body.append('name', name);
        body.append('institution_id', institution.id);
        body.append('mapping', JSON.stringify(mapping));
        body.append('settings', JSON.stringify({ width_mm: width, height_mm: height, bleed_mm: bleed, max_chars: { full_name: 50 } }));
        await api('/templates', { method: 'POST', body });
        await query.refetch();
        setMessage('Template registered. Run Inspect and review the result in Production.');
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    return <><div className="heading"><div><div className="eyebrow">DESIGN LIBRARY</div><h1>CorelDRAW templates</h1><p className="muted">Use your existing CorelDRAW 2019 designs.</p></div></div>{error && <div className="error">{error}</div>}{message && <div className="notice">{message}</div>}<div className="grid two"><section className="card"><h2>Registered designs</h2>{query.data?.map(t => <div className="list-row" key={t.id}><div><h3>{t.name}</h3><small>{t.settings.width_mm} × {t.settings.height_mm} mm</small></div><Button variant="outline" onClick={async () => { try {
        await api(`/templates/${t.id}/inspect`, { method: 'POST' });
        setMessage('Inspection queued. See Production for named objects and dimensions.');
    }
    catch (e) {
        setError((e as Error).message);
    } }}>Inspect template</Button></div>)}{!query.data?.length && <div className="empty">Register a design to begin production.</div>}<div className="notice">Name objects in CorelDRAW’s Objects docker. Visible placeholder text is separate from the object name. Use an empty closed photo frame. Front and back belong on pages 1 and 2 of the same CDR.</div></section><section className="card"><h2>Register template</h2><div className="fields"><label className="field full">Design name<input value={name} onChange={e => setName(e.target.value)}/></label><label className="field full">CorelDRAW file<input type="file" accept=".cdr" onChange={e => setFile(e.target.files?.[0] || null)}/></label><label className="field">Card width (mm)<input type="number" min="10" step="0.1" value={width} onChange={e => setWidth(+e.target.value)}/></label><label className="field">Card height (mm)<input type="number" min="10" step="0.1" value={height} onChange={e => setHeight(+e.target.value)}/></label><label className="field">Bleed per edge (mm)<input type="number" min="0" step="0.1" value={bleed} onChange={e => setBleed(+e.target.value)}/></label></div><div className="divider"/><h3>Named object → student field</h3><p className="help">Names must occur exactly once across both pages. Use separate object names for back-side fields; they can map to the same student field.</p>{Object.entries(mapping).map(([key, value], i) => <div className="actions" style={{ marginTop: 9 }} key={i}><input className="input" style={{ width: '45%' }} aria-label="CorelDRAW object name" defaultValue={key} onBlur={e => { const updated = { ...mapping }; delete updated[key]; updated[e.target.value] = value; setMapping(updated); }}/><select className="input" style={{ width: '40%' }} aria-label="Mapped student field" value={value} onChange={e => setMapping({ ...mapping, [key]: e.target.value })}><option value="photo">Approved photo</option>{institution.fields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}</select><button aria-label="Remove mapping" onClick={() => { const m = { ...mapping }; delete m[key]; setMapping(m); }}>×</button></div>)}<div className="actions" style={{ marginTop: 20 }}><Button variant="outline" onClick={() => setMapping({ ...mapping, ['OBJECT_' + Object.keys(mapping).length]: 'full_name' })}>Add mapping</Button><Button disabled={busy || !name || !file} onClick={save}>Save template</Button></div></section></div></>;
}
export function Production() {
    const query = useQuery({ queryKey: ['jobs'], queryFn: () => api<Job[]>('/jobs'), refetchInterval: 2500 });
    const [error, setError] = useState(''), [selected, setSelected] = useState<Job | null>(null), [sheet, setSheet] = useState({ width: 210, height: 297, card_width: 85.6, card_height: 54, margin: 10, gap: 5, bleed: 0, duplex: 'none', cutting_marks: true }), [output, setOutput] = useState('');
    async function action(job: Job, operation: string) { try {
        await api(`/jobs/${job.id}/${operation}`, { method: 'POST' });
        await query.refetch();
    }
    catch (e) {
        setError((e as Error).message);
    } }
    return <><div className="heading"><div><div className="eyebrow">PRODUCTION DESK</div><h1>Production jobs</h1><p className="muted">Cards are generated sequentially in your interactive Windows session.</p></div></div>{error && <div className="error">{error}</div>}<div className="grid">{query.data?.map(job => { const items = Object.entries(job.result?.items || {}) as [
        string,
        any
    ][]; const done = items.filter(([, v]) => v.state === 'completed').length; return <section className="card" key={job.id}><div className="actions" style={{ justifyContent: 'space-between' }}><div><h2>{job.kind === 'inspect' ? 'Template inspection' : job.payload.template?.name || 'Card production'}</h2><small>{new Date(job.created).toLocaleString()} · {job.id.slice(0, 8)}</small></div><span className={'badge ' + (job.state === 'completed' ? '' : 'pending')}>{job.state}</span></div>{job.kind === 'generate' && <><div className="progress"><span style={{ width: `${done / Math.max(1, job.payload.students?.length) * 100}%` }}/></div><p className="muted">{done} / {job.payload.students?.length} cards complete</p></>}{job.result.error && <div className="error">{job.result.error}</div>}{job.result.inspection && <pre>{JSON.stringify(job.result.inspection, null, 2)}</pre>}{items.map(([id, item]) => <div className="list-row" key={id}><div>{job.payload.students?.find((s: any) => s.id === id)?.data.full_name || id}<small>{item.error || item.state}</small></div>{item.state === 'completed' && <div className="actions"><a href={asset(item.cdr)}>CDR</a><a target="_blank" rel="noreferrer" href={asset(item.pdf)}>Inspect PDF</a></div>}</div>)}<div className="actions" style={{ marginTop: 15 }}>{['failed', 'partial', 'interrupted'].includes(job.state) && <Button variant="outline" onClick={() => action(job, 'retry')}>Retry failed cards</Button>}{['queued', 'interrupted'].includes(job.state) && <Button variant="ghost" onClick={() => action(job, 'cancel')}>Cancel</Button>}{job.kind === 'generate' && ['completed', 'partial'].includes(job.state) && <><Button variant="outline" onClick={() => { setSelected(job); setOutput(''); const t = job.payload.template.settings; setSheet({ ...sheet, card_width: t.width_mm, card_height: t.height_mm, bleed: t.bleed_mm || 0 }); }}>Arrange print sheets</Button><a className="button outline" href={`/api/jobs/${job.id}/zip`}>Download ZIP</a></>}</div></section>; })}{!query.data?.length && <div className="card empty">Select students in Student Records, choose a template, and generate cards.</div>}</div>{selected && <section className="card" style={{ marginTop: 20 }}><h2>Print sheets · {selected.payload.template.name}</h2><p className="help">PDF page dimensions must match the card plus bleed. Print at 100% / Actual size. Duplex alignment requires a physical test sheet.</p><div className="fields">{(['width', 'height', 'card_width', 'card_height', 'margin', 'gap', 'bleed'] as const).map(k => <label className="field" key={k}>{k.replace('_', ' ')} (mm)<input type="number" step="0.1" value={sheet[k]} onChange={e => setSheet({ ...sheet, [k]: +e.target.value })}/></label>)}<label className="field">Duplex<select value={sheet.duplex} onChange={e => setSheet({ ...sheet, duplex: e.target.value })}><option value="none">Front only (one-page cards)</option><option value="long-edge">Front/back · flip long edge</option><option value="short-edge">Front/back · flip short edge</option></select></label><label className="inline-label"><input type="checkbox" checked={sheet.cutting_marks} onChange={e => setSheet({ ...sheet, cutting_marks: e.target.checked })}/>Cutting marks</label></div><div className="actions" style={{ marginTop: 20 }}><Button onClick={async () => { try {
        const r = await api<{
            path: string;
        }>(`/jobs/${selected.id}/sheets`, { method: 'POST', body: JSON.stringify(sheet) });
        setOutput(r.path);
    }
    catch (e) {
        setError((e as Error).message);
    } }}>Create print PDF</Button>{output && <a target="_blank" rel="noreferrer" href={asset(output)}>Open print-ready sheet PDF</a>}</div></section>}</>;
}
