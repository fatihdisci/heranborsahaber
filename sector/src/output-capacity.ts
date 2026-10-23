/** Counts only: never source bodies, credentials or delivery state. */
export interface CapacityDiagnostic {
 version:1;
 kind:'visual'|'tweet';
 fields?:{name:string;rows:number;per_card:number}[];
 required_cards?:number;
 max_cards?:number;
 events?:number;
 tickers?:number;
 tweet_length?:number;
 tweet_limit?:number;
 preference?:'default_summary'|'all'|'first';
 selected_tickers?:number;
 fit_tickers?:number;
 hashtag_tweet_length?:number;
}
export class OutputCapacityError extends Error {
 constructor(code:string,public diagnostic:CapacityDiagnostic){super(code);}
}
export function capacityMessage(code:string,value?:CapacityDiagnostic):string|undefined {
 if(code==='tweet_capacity_exceeded'&&value?.selected_tickers!==undefined)return `Seçilen ${value.selected_tickers} hisse kodu başlık ve zorunlu kapsam notuyla hashtagsiz ${value.tweet_length}/${value.tweet_limit??280} karakter${value.hashtag_tweet_length!==undefined?'; # ile '+value.hashtag_tweet_length+' karakter':''}. Aynı öncelik sırasında en fazla ${value.fit_tickers??0} kod sığıyor. Hiçbir kod kendiliğinden çıkarılmadı; görsel veya yayın oluşturulmadı. Daha az kodu açıkça seçmen gerekir; otomatik thread açılmadı.`;
 if(code==='tweet_capacity_exceeded')return `Tweet metni X’in ${value?.tweet_limit??280} karakter sınırını aşıyor${value?.tweet_length!==undefined?' ('+value.tweet_length+' karakter)':''}. ${value?.preference==='all'?'Açık tüm-hisseler tercihin korunuyor; hiçbir kod çıkarılmadı. ':''}Bu hata tweet metnine ait; görsel üretimi başlamadı. Kısa tweet özeti için kapsam tercihini değiştirmen gerekir; otomatik thread açılmadı.`;
 if(code==='multi_card_capacity_exceeded'){
  const field=value?.fields?.find(f=>f.name==='report.rows');
  if(field&&value?.required_cards&&value.max_cards)return `${value.events!==undefined?value.events+' bildirim, ':''}${value.tickers??field.rows} farklı hisse var. Mevcut günlük rapor düzeni kart başına ${field.per_card}, ${value.max_cards} kartta ${field.per_card*value.max_cards} hisse destekliyor; bu liste ${value.required_cards} kart gerektiriyor.${value.tweet_length!==undefined&&value.tweet_limit!==undefined?' Tweet metni '+value.tweet_length+'/'+value.tweet_limit+' karakter; '+(value.tweet_length<=value.tweet_limit?'tweet sınırı sorun değil.':'tweet sınırı da aşılıyor.'):''} Hiçbir satır çıkarılmadı, gönderim yapılmadı. Tüm liste için yeni bir tablo düzeni veya açık kapsam seçimi gerekiyor; otomatik thread açılmadı.`;
  return 'Seçilen verinin görsel kapasitesi aşıldı. En fazla dört görsel destekleniyor. Hiçbir satır çıkarılmadı; bu hata tweet uzunluğundan kaynaklanmıyor. Otomatik thread açılmadı.';
 }
 if(/(?:report|general|buyback|market|circuit|card|cell|footer).*capacity_exceeded/.test(code))return 'Görseldeki satır, hücre veya metin mevcut şablonun okunaklı kapasitesine sığmıyor. Hiçbir veri çıkarılmadı; bu hata tweet uzunluğu değildir. Gönderim yapılmadı.';
 if(/caption_limit|caption_too_long/.test(code))return 'Telegram açıklama metni sınırı aşıldı. Hiçbir hisse kodu çıkarılmadı ve gönderim yapılmadı. Bu hata görsel kapasitesinden ayrıdır.';
}
