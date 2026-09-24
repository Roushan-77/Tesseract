const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export type Case = { id:string; case_number:string; title:string; status:string; priority:string; summary?:string; created_at?:string; updated_at:string; lead_investigator?:User; assignments?:{assignment_role:string;user:User}[] };
export type User = { id:string; investigator_id:string; name:string; role:string };
export type EntityMention = {mentionId:string;type:string;text:string;normalizedValue:string;start:number;end:number;confidence:number};
export type Extraction = {
  evidence_id: string;
  processing_status: string;
  ocr_status: string;
  extraction_status: string;
  language: { code: string; confidence: number } | null;
  text: string | null;
  pages: string[] | null;
  entities: EntityMention[];
  categories: Record<string, EntityMention[]>;
  warnings: string[];
  error: string | null;
  processed_at: string | null;
  ingestion_method?: string;
  structured?: {
    records?: Array<Record<string, any> | { row?: number; fields?: Record<string, any> }>;
    row_count?: number;
    rowCount?: number;
    column_count?: number;
    columns?: string[];
    file_type?: string;
    method?: string;
    summary?: string;
    sheets?: Record<string, { columns: string[]; rows: any[][] }>;
  } | null;
  relations?: Array<{
    type: string;
    source: EntityMention;
    target: EntityMention;
    sourceText: string;
    confidence: number;
    sourceRow?: number;
    sourceFields?: string[];
  }>;
  events?: Array<{
    type: string;
    date?: string | null;
    location?: EntityMention | null;
    participants: EntityMention[];
    sourceText: string;
    confidence: number;
    sourceRow?: number;
  }>;
};
export type Evidence = {
  id?: string;
  evidence_id: string;
  case_id?: string;
  case_number?: string | null;
  filename: string;
  document_type: string;
  mime_type: string;
  document_language: string | null;
  uploaded_by: User;
  uploaded_at: string;
  ocr_status: string;
  extraction_status: string;
  integrity_status: string;
  processing_status: string;
  processing_error: string | null;
  notes: string | null;
  ingestion_method?: string;
  structured_json?: any;
};
export type RelatedCase = {case_number:string;title:string;status:string;investigating_officer:string;access_level:"FULL"|"RESTRICTED"};
export type Prompt4Mention = {id:string;entity_id:string|null;entity_type:string;text:string;normalized_value:string;confidence:number;resolution_status:string;resolution_confidence:number|null;evidence_id:string};
export type IntelligenceEntity = {id:string;entity_type:string;canonical_name:string;mentions:Prompt4Mention[];evidence_count:number};
export type Resolution = {id:string;source:Prompt4Mention;target:Prompt4Mention;confidence:number;reasons:string[];status:string};
export type Relation = {id:string;relation_type:string;source:Prompt4Mention;target:Prompt4Mention;confidence:number;evidence_id:string;source_text:string;observed_at:string|null};
export type Event = {id:string;event_type:string;evidence_id:string;event_date:string|null;event_time:string|null;location:string|null;participants:Prompt4Mention[];confidence:number;source_text:string};
export type Integrity = {evidence_id:string;sha256:string|null;current_hash?:string|null;ledger_record_id:string|null;status:string;verified:boolean;file_size:number|null;registered_at:string|null;verified_at:string|null};
export type AuditEvent = {id:string;timestamp:string;actor_id:string|null;actor?:User|null;action:string;resource_type:string;resource_id:string|null;case_id:string|null;case_number?:string|null;result:string;metadata_json:Record<string, unknown>};
export type AccessRequest = {id:string;requester_id:string;case_id:string;resource_id:string|null;status:string;reason:string;created_at:string;reviewed_at:string|null;reviewed_by_id:string|null};
export type InvestigationFlag = {
  id: string;
  case_id: string;
  case_number: string;
  resource_type: string;
  resource_id: string;
  resource_label: string;
  flagged_by: User;
  reason: string;
  status: string;
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: User | null;
  resolution_notes?: string | null;
};
export async function api<T>(path:string, token:string): Promise<T> { const response = await fetch(`${base}${path}`, { headers:{ Authorization:`Bearer ${token}` }, cache:"no-store" }); if (!response.ok) { const detail=await response.text(); throw new Error(`API ${response.status}: ${detail || "Unable to load data"}`); } return response.json(); }
export async function apiPost<T>(path:string, token:string, body:FormData|object):Promise<T>{const form=body instanceof FormData;const response=await fetch(`${base}${path}`,{method:"POST",headers:{Authorization:`Bearer ${token}`,...(form?{}:{"Content-Type":"application/json"})},body:form?body:JSON.stringify(body)});if(!response.ok)throw new Error(await response.text());return response.json()}
export async function apiDelete<T>(path:string, token:string):Promise<T>{const response=await fetch(`${base}${path}`,{method:"DELETE",headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error(await response.text());return response.json()}
export function getProcessingMethod(doc: { filename: string; document_type?: string; mime_type?: string; ingestion_method?: string }): "OCR" | "Text Extraction" | "Structured Parsing" {
  const ext = (doc.filename.split('.').pop() || '').toLowerCase();
  const docType = (doc.document_type || '').toLowerCase();
  const mime = (doc.mime_type || '').toLowerCase();
  const ingestion = (doc.ingestion_method || '').toLowerCase();

  if (['csv', 'xls', 'xlsx', 'json', 'xml', 'cdr'].includes(ext) || ['csv', 'xls', 'xlsx', 'json', 'xml', 'cdr'].includes(docType) || ingestion === 'structured') {
    return "Structured Parsing";
  }
  if (['txt', 'doc', 'docx'].includes(ext) || ['txt', 'doc', 'docx'].includes(docType) || mime.includes('text/plain') || mime.includes('wordprocessingml') || mime.includes('msword')) {
    return "Text Extraction";
  }
  return "OCR";
}
export { base };
