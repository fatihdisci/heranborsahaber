/** Normalize unsupported typographic minus glyphs while preserving em dashes used for missing data. */
export function normalizeCardText(value:string):string{return value.replace(/\u2212/g,'-');}
