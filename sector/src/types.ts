export type Category = 'turkiye'|'central_banks'|'companies'|'technology'|'energy'|'global'|'data'|'bist'|'kap';
export type Template = 'breaking'|'economic_data'|'company'|'global'|'info'|'circuit'|'kap'|'market'|'finance'|'news'|'institutional'|'akd'|'volume';
export type Status = 'pending'|'deferred'|'rejected'|'approved'|'needs_review'|'published';
export interface Source {
  id:string; name:string; url:string; family:string; language:string; official:boolean;
  allowed_hosts:string[]; poll_seconds:number; fresh_hours:number; enabled:boolean;
  editorial_priority?:number; minimum_score?:number;
  checked_at:string; terms_url:string; rights_note:string; review_mode:string;
  article_mode?:'html'|'feed_only';
  method?:'rss'|'bridge_pdf'|'reference';
}
export interface Item {title:string;url:string;summary:string;published_at:string|null;}
export interface Document {source_id:string;source_name:string;family:string;official:boolean;url:string;title:string;body:string;published_at:string|null;passages:{id:string;text:string}[];primary_urls?:string[];equity_codes?:string[];index_tier?:30|100;language?:string;images?:string[];coverage?:{complete:boolean;page_count:number;pages:unknown[]};}
export interface Evidence {document:number;passage:string;quote:string;}
export interface Claim {text:string;evidence:Evidence[];}
export interface CardRow {label:string;value:string;}
export interface CardData {ticker?:string;as_of?:string;buy?:CardRow[];sell?:CardRow[];metrics?:CardRow[];}
export interface Draft {
  card_data?:CardData;
  headline:string;body:string;hashtags:string[];category:Category;importance:number;
  template:Template;claims:Claim[];entities:string[];event_key:string;uncertainties:string[];source_notes?:string[];
  card_headline:string;card_body:string;
}
export interface Env {
  DB:D1Database; MEDIA:R2Bucket;
  MODE:'dry_run'|'telegram_review';
  ADMIN_TOKEN?:string; BRIDGE_TOKEN?:string; AI_MODEL:string; AI_EFFORT:'medium';
  TELEGRAM_BOT_TOKEN?:string; TELEGRAM_CHAT_ID?:string; TELEGRAM_USER_ID?:string;
  TELEGRAM_UPDATE_ID?:number;
  KAP_DELIVERY_CHECK?:(documents:Document[])=>'allow'|'suppress'|'hold';
  TELEGRAM_WEBHOOK_SECRET?:string; TELEGRAM_VERIFIED_BOT_ID?:string;
  AI_DAILY_DRAFT_LIMIT:string;
}
