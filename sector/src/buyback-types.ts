export interface BuybackRow {ticker:string;day:string;nominal:string|null;price:string|null;amount:string|null;raw:(string|null)[];ocr_original?:(string|null)[];}
export interface BuybackTable {day:string;rows:BuybackRow[];row_count:number;reader:string;}
export interface BuybackEvidence {selection?:BuybackSelectionEvidence;original_key?:string;report_url:string;image_url:string;image_hash:string;published_at:string;version:string;index_checked_at:string|null;index_source:string|null;reader:string;raw_rows:BuybackRow[];}

export interface BuybackIndexSnapshot {schema_version:1;source_url:string;retrieved_at:string;sha256:string;members:{bist30:string[];bist100:string[]};}
export interface BuybackSelectionEvidence {algorithm:'index-nominal-v1';transaction_date:string;evaluated_at:string;index_snapshot:BuybackIndexSnapshot|null;selected:{ticker:string;rank:number;nominal:string|null;reason:'BIST30'|'BIST100'|'other'|'membership_unknown'}[];}
