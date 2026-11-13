'use client';
import { useState } from 'react';
import { Plus, Trash2, ArrowUp, Building2 } from 'lucide-react';
import { Button } from './ui/button';
import { api, asset, type Field, type Institution } from '@/lib/api';
export const defaultFields: Field[] = [{ key: 'full_name', label: 'Full name', type: 'text', required: true }, { key: 'student_id', label: 'Student ID', type: 'text', required: true }, { key: 'class', label: 'Class / department', type: 'text', repeat: true }, { key: 'division', label: 'Division', type: 'text', repeat: true }, { key: 'blood_group', label: 'Blood group', type: 'select', options: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'Unknown'] }, { key: 'date_of_birth', label: 'Date of birth', type: 'date' }];
export function Projects({ institutions, onSelect, onChanged }: {
    institutions: Institution[];
    onSelect: (id: string) => void;
    onChanged: () => void;
}) {
    const [editing, setEditing] = useState<string | null>(null), [name, setName] = useState(''), [year, setYear] = useState('2026–2027'), [fields, setFields] = useState<Field[]>(defaultFields), [error, setError] = useState(''), [busy, setBusy] = useState(false);
    const patch = (i: number, change: Partial<Field>) => setFields(fields.map((f, n) => n === i ? { ...f, ...change } : f));
    async function save() { setBusy(true); setError(''); try {
        const inst = await api<Institution>('/institutions' + (editing ? '/' + editing : ''), { method: editing ? 'PUT' : 'POST', body: JSON.stringify({ name, year, fields }) });
        onChanged();
        onSelect(inst.id);
        setEditing(null);
        setName('');
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    return <><div className="heading"><div className="eyebrow">CLIENT WORKSPACE</div><h1>Schools & colleges</h1></div>{error && <div className="error">{error}</div>}<div className="grid two"><section className="card"><h2>Your institutions</h2>{institutions.map(inst => <div className="list-row" key={inst.id}><div className="actions">{inst.logo ? <img className="institution-logo" src={asset(inst.logo)} alt="Institution logo"/> : <Building2 />}<div><h3>{inst.name}</h3><small>{inst.year} · {inst.fields.length} fields</small></div></div><div className="actions"><Button variant="ghost" onClick={() => { setEditing(inst.id); setName(inst.name); setYear(inst.year); setFields(inst.fields); }}>Edit</Button><Button variant="outline" onClick={() => onSelect(inst.id)}>Open</Button></div></div>)}{!institutions.length && <div className="empty">Create your first school or college to start registering students.</div>}</section><section className="card"><h2>{editing ? 'Edit institution' : 'New institution'}</h2>{editing && <label className="field" style={{ marginBottom: 16 }}>Institution logo<input type="file" accept="image/jpeg,image/png" onChange={async (e) => { const file = e.target.files?.[0]; e.target.value = ''; if (!file)
        return; try {
        const body = new FormData();
        body.append('file', file);
        await api(`/institutions/${editing}/logo`, { method: 'POST', body });
        onChanged();
    }
    catch (error) {
        setError((error as Error).message);
    } }}/></label>}<div className="fields"><label className="field">Institution name<input value={name} onChange={e => setName(e.target.value)}/></label><label className="field">Academic year<input value={year} onChange={e => setYear(e.target.value)}/></label></div><div className="divider"/><h3>Registration fields</h3><p className="help">Field keys are used by CSV imports and template mappings. Keep full_name.</p>{fields.map((f, i) => <div className="card" style={{ padding: 12, marginTop: 10 }} key={i}><div className="fields"><label className="field">Label<input value={f.label} onChange={e => patch(i, { label: e.target.value })}/></label><label className="field">Key<input value={f.key} onChange={e => patch(i, { key: e.target.value })}/></label><label className="field">Type<select value={f.type} onChange={e => patch(i, { type: e.target.value as Field['type'] })}><option value="text">Text</option><option value="date">Date</option><option value="select">Dropdown</option></select></label><div className="actions"><label className="inline-label"><input type="checkbox" checked={!!f.required} onChange={e => patch(i, { required: e.target.checked })}/>Required</label><label className="inline-label"><input type="checkbox" checked={!!f.repeat} onChange={e => patch(i, { repeat: e.target.checked })}/>Keep for next</label></div>{f.type === 'select' && <label className="field full">Options, separated by commas<input value={f.options?.join(',') || ''} onChange={e => patch(i, { options: e.target.value.split(',') })}/></label>}</div><div className="actions" style={{ marginTop: 7 }}><Button variant="ghost" disabled={!i} aria-label="Move field up" onClick={() => { const a = [...fields]; [a[i - 1], a[i]] = [a[i], a[i - 1]]; setFields(a); }}><ArrowUp size={14}/></Button><Button variant="ghost" aria-label="Remove field" disabled={f.key === 'full_name'} onClick={() => setFields(fields.filter((_, n) => n !== i))}><Trash2 size={14}/></Button></div></div>)}<div className="actions" style={{ marginTop: 18 }}><Button variant="outline" onClick={() => setFields([...fields, { key: 'custom_' + fields.length, label: 'Custom field', type: 'text' }])}><Plus size={14}/>Add field</Button><Button disabled={busy || !name} onClick={save}>Save institution</Button>{editing && <Button variant="ghost" onClick={() => { setEditing(null); setName(''); setFields(defaultFields); }}>New instead</Button>}</div></section></div></>;
}
