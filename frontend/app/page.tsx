'use client';
import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { LayoutDashboard, Building2, UserPlus, Users, Layers, Printer, Settings as SettingsIcon, Contact, Camera, CheckCircle2, ArrowRight, FileCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Registration } from '@/components/registration';
import { Projects } from '@/components/projects';
import { Records } from '@/components/records';
import { Templates, Production } from '@/components/production';
import { Settings } from '@/components/settings';
import { api, type Institution, type Student, type Job } from '@/lib/api';
const tabs = [['Dashboard', LayoutDashboard], ['Schools & colleges', Building2], ['Registration', UserPlus], ['Student records', Users], ['Templates', Layers], ['Production', Printer], ['Settings', SettingsIcon]] as const;
function Studio() {
    const cache = useQueryClient();
    const [tab, setTab] = useState('Dashboard'), [institutionId, setInstitutionId] = useState(''), [existing, setExisting] = useState<Student | null>(null), [registrationKey, setRegistrationKey] = useState(0), [auth, setAuth] = useState(false), [launchToken, setLaunchToken] = useState(''), [password, setPassword] = useState(''), [error, setError] = useState('');
    useEffect(() => { const hash = new URLSearchParams(location.hash.slice(1)); const token = hash.get('token'); if (token) {
        setLaunchToken(token);
        history.replaceState(null, '', location.pathname);
        api('/unlock', { method: 'POST', body: JSON.stringify({ token }) }).then(() => setAuth(true)).catch(e => setError(e.message));
    }
    else
        api('/dashboard').then(() => setAuth(true)).catch(() => setError('Open the app using Start ID Card Studio.')); }, []);
    const institutions = useQuery({ queryKey: ['institutions'], queryFn: () => api<Institution[]>('/institutions'), enabled: auth });
    const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: () => api<Record<string, number>>('/dashboard'), enabled: auth, refetchInterval: 10000 });
    const hardware = useQuery({ queryKey: ['settings'], queryFn: () => api('/settings'), enabled: auth, refetchInterval: 5000 });
    const jobs = useQuery({ queryKey: ['jobs'], queryFn: () => api<Job[]>('/jobs'), enabled: auth, refetchInterval: 5000 });
    const institution = institutions.data?.find(i => i.id === institutionId) || institutions.data?.[0];
    const refresh = () => { void cache.invalidateQueries({ queryKey: ['institutions'] }); void cache.invalidateQueries({ queryKey: ['dashboard'] }); void cache.invalidateQueries({ queryKey: ['students'] }); };
    const edit = (s: Student) => { setExisting(s); setRegistrationKey(k => k + 1); setTab('Registration'); };
    const next = async () => { refresh(); if (existing && institution) {
        const pending = await api<Student[]>('/students?institution_id=' + institution.id + '&status=pending');
        if (pending.length)
            edit(pending[0]);
        else {
            setExisting(null);
            setTab('Student records');
        }
    } };
    if (!auth)
        return <div className="card unlock"><Contact size={38}/><h1>ID Card Studio</h1><p className="muted">Your local production workstation</p>{error && <div className="notice">{error}</div>}{launchToken && <form onSubmit={async (e) => { e.preventDefault(); try {
            await api('/unlock', { method: 'POST', body: JSON.stringify({ token: launchToken, password }) });
            setAuth(true);
            setError('');
        }
        catch (e) {
            setError((e as Error).message);
        } }}><label className="field">Owner password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password"/></label><Button style={{ marginTop: 15 }}>Unlock studio</Button></form>}</div>;
    const online = hardware.data?.agent?.seen && Date.now() - Date.parse(hardware.data.agent.seen) < 15000;
    return <div className="shell"><aside className="sidebar"><div className="brand"><Contact /><div>ID Card Studio<small>PRODUCTION WORKSPACE</small></div></div><nav>{tabs.map(([name, Icon]) => <button key={name} className={'nav-item ' + (tab === name ? 'active' : '')} onClick={() => { setTab(name); setError(''); if (name === 'Registration') {
        setExisting(null);
        setRegistrationKey(k => k + 1);
    } }}><Icon size={18}/>{name}</button>)}</nav><footer><span className="dot"/>Local workstation<br /><span style={{ color: '#8faab6' }}>Private storage · Single owner</span></footer></aside><div className="workspace"><header className="topbar"><span className="muted">Workspace / <strong>{tab}</strong></span><div className="actions"><select className="input" aria-label="Current institution" value={institution?.id || ''} onChange={e => { setInstitutionId(e.target.value); setExisting(null); setRegistrationKey(k => k + 1); }}><option value="" disabled>Select institution</option>{institutions.data?.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}</select><span className={'badge ' + (online ? '' : 'pending')}>Agent {online ? hardware.data.agent.status : 'offline'}</span></div></header><main className="content">{error && <div className="error">{error}</div>}{institutions.error && <div className="error">{institutions.error.message}</div>}
 {tab === 'Dashboard' && <><div className="heading"><div><div className="eyebrow">YOUR PRODUCTION OVERVIEW</div><h1>Welcome to your studio</h1><p className="muted">From student registration to print-ready cards, all in one place.</p></div><Button onClick={() => { setExisting(null); setRegistrationKey(k => k + 1); setTab(institution ? 'Registration' : 'Schools & colleges'); }}><UserPlus size={16}/>Register student</Button></div><div className="grid stats">{[['institutions', 'Client institutions', Building2], ['students', 'Student records', Users], ['pending', 'Photos pending', Camera], ['ready', 'Ready to generate', Contact], ['generated', 'Cards generated', FileCheck], ['printed', 'Cards printed', CheckCircle2]].map(([key, label, Icon]) => { const I = Icon as typeof Users; return <div className="card stat" key={key as string}><div><span className="muted">{label as string}</span><strong>{dashboard.data?.[key as string] ?? '—'}</strong></div><I /></div>; })}</div><div className="grid two"><section className="card"><div className="actions" style={{ justifyContent: 'space-between' }}><h2>Recent projects</h2><Button variant="ghost" onClick={() => setTab('Schools & colleges')}>View all<ArrowRight size={14}/></Button></div>{institutions.data?.slice(0, 5).map(i => <div className="list-row" key={i.id}><div><h3>{i.name}</h3><small>{i.year}</small></div><Button variant="outline" onClick={() => { setInstitutionId(i.id); setTab('Student records'); }}>Open project</Button></div>)}{!institutions.data?.length && <div className="empty"><Building2 style={{ margin: '0 auto 12px' }}/><p>Start with your first institution.</p><Button onClick={() => setTab('Schools & colleges')}>Create institution</Button></div>}</section><section className="card"><h2>Production activity</h2>{jobs.data?.slice(0, 5).map(j => <div className="list-row" key={j.id}><div><h3>{j.payload.template?.name || 'Production job'}</h3><small>{j.kind} · {new Date(j.created).toLocaleString()}</small></div><span className="badge">{j.state}</span></div>)}{!jobs.data?.length && <div className="empty">No production jobs yet.<br />Approved student photos and a registered design get you started.</div>}<div className="notice">Before the first batch, generate one card and verify its text, photo, dimensions, fonts, and print alignment.</div></section></div></>}
 {tab === 'Schools & colleges' && <Projects institutions={institutions.data || []} onChanged={refresh} onSelect={id => { setInstitutionId(id); setTab('Student records'); }}/>}
 {['Registration', 'Student records', 'Templates'].includes(tab) && !institution && <div className="card empty"><p>Create an institution first.</p><Button onClick={() => setTab('Schools & colleges')}>Create institution</Button></div>}
 {tab === 'Registration' && institution && <Registration key={`${institution.id}-${registrationKey}`} institution={institution} existing={existing} onSaved={refresh} onNext={() => { void next().catch(e => setError(e.message)); }}/>}
 {tab === 'Student records' && institution && <Records key={institution.id} institution={institution} onEdit={edit} onProduced={() => setTab('Production')}/>}
 {tab === 'Templates' && institution && <Templates key={institution.id} institution={institution}/>}
 {tab === 'Production' && <Production />}{tab === 'Settings' && <Settings />}
 </main></div></div>;
}
export default function Page() { const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })); return <QueryClientProvider client={client}><Studio /></QueryClientProvider>; }
