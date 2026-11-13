export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch('/api' + path, { ...options, headers: { 'X-IDCS-Request': '1', ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
    }
    return response.json();
}
export const asset = (path: string) => '/api/assets/' + path.split('/').map(encodeURIComponent).join('/');
export type Field = {
    key: string;
    label: string;
    type: 'text' | 'date' | 'select';
    required?: boolean;
    repeat?: boolean;
    options?: string[];
};
export type Institution = {
    id: string;
    name: string;
    year: string;
    fields: Field[];
    logo?: string;
};
export type Student = {
    id: string;
    institution_id: string;
    data: Record<string, string>;
    photo_id: string | null;
    revision: number;
    status: string;
};
export type Capture = {
    id: string;
    student_id: string;
    state: string;
    original: string | null;
    approved: string | null;
};
export type Template = {
    id: string;
    name: string;
    mapping: Record<string, string>;
    settings: Record<string, any>;
};
export type Job = {
    id: string;
    kind: string;
    state: string;
    created: string;
    payload: any;
    result: any;
};
