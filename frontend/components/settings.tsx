'use client';
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from './ui/button';
import { api } from '@/lib/api';
export function Settings() {
    const query = useQuery({ queryKey: ['settings'], queryFn: () => api('/settings'), refetchInterval: 5000 });
    const [folder, setFolder] = useState(''), [days, setDays] = useState(30), [password, setPassword] = useState(''), [message, setMessage] = useState(''), [error, setError] = useState('');
    useEffect(() => { if (query.data) {
        setFolder(query.data.preferences.watch_folder);
        setDays(query.data.preferences.retention_days);
    } }, [query.data?.preferences.watch_folder, query.data?.preferences.retention_days]);
    const run = async (fn: () => Promise<void>) => { setError(''); try {
        await fn();
        setMessage('Settings saved.');
        await query.refetch();
    }
    catch (e) {
        setError((e as Error).message);
    } };
    return <><div className="heading"><div><div className="eyebrow">LOCAL WORKSTATION</div><h1>Settings & diagnostics</h1><p className="muted">One computer. Local files. No cloud connection for daily work.</p></div></div>{error && <div className="error">{error}</div>}{message && <div className="notice">{message}</div>}<div className="grid two"><section className="card"><h2>Camera reception</h2><label className="field">Nikon tether output folder<input placeholder="C:\Photos\Nikon" value={folder} onChange={e => setFolder(e.target.value)}/></label><p className="help">Set the same destination in compatible Nikon tethering software. JPEG/PNG only. Existing files are ignored when switching folders. New arrivals remain unassigned until selected.</p><div className="divider"/><label className="field">Unreferenced file retention (days)<input type="number" min="1" value={days} onChange={e => setDays(+e.target.value)}/></label><p className="help">Run scripts/cleanup.ps1 with the application stopped. Active records and job photos are retained.</p><Button onClick={() => run(async () => { await api('/settings', { method: 'PUT', body: JSON.stringify({ watch_folder: folder, retention_days: days }) }); })}>Save settings</Button><div className="divider"/><h2>Owner password</h2><label className="field">New password (at least 10 characters)<input type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)}/></label><Button style={{ marginTop: 12 }} onClick={() => run(async () => { await api('/settings/password', { method: 'POST', body: JSON.stringify({ password }) }); setPassword(''); })}>Set password</Button><p className="help">Password is requested when opening a new authenticated browser session.</p></section><section className="card"><h2>Hardware agent</h2><pre>{JSON.stringify(query.data?.agent || { status: 'offline' }, null, 2)}</pre><h3>Private data directory</h3><pre>{query.data?.data_directory}</pre><div className="notice">CorelDRAW 21 and your Nikon camera must be verified on this Windows PC. Direct Nikon SDK capture is not enabled. Run diagnose.ps1 -CorelTest to test the registered automation server.</div><h3>Backup & restore</h3><p className="help">Close the application, then run backup.ps1. Restore with restore.ps1 -Archive &quot;C:\path\backup.zip&quot;. Restore retains the previous data directory for rollback. Backups contain student data; keep them on protected storage.</p></section></div></>;
}
