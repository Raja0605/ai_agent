import { API_BASE_URL } from '../config/api';
import { mapJob } from './jobService';
import type { JobPost } from '../types/job';
export interface McpServer { id: string; name: string; transport: McpTransport; endpoint: string; enabled: boolean; status: string; }
export type McpTransport = 'stdio' | 'sse' | 'streamable-http';
export interface McpServerCreate { name: string; transport: McpTransport; endpoint: string; enabled?: boolean; }
export async function listMcpServers(): Promise<McpServer[]> { const r = await fetch(`${API_BASE_URL}/mcp/servers`); if (!r.ok) throw new Error('Could not load MCP servers'); return r.json(); }
export async function createMcpServer(payload: McpServerCreate): Promise<McpServer> { const r = await fetch(`${API_BASE_URL}/mcp/servers`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); if (!r.ok) throw new Error('Could not save MCP server'); return r.json(); }
export async function testMcpServer(id: string) { const r = await fetch(`${API_BASE_URL}/mcp/servers/${id}/test`, {method:'POST'}); if (!r.ok) throw new Error('MCP unavailable'); return r.json(); }
export async function searchMcp(server_ids: string[], keywords: string[], location?: string, remote?: boolean): Promise<JobPost[]> { const r = await fetch(`${API_BASE_URL}/mcp/search`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({server_ids, keywords, location, remote})}); if (!r.ok) throw new Error('MCP search failed'); const data = await r.json(); return (data.results || []).map(mapJob); }
