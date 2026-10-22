// Only owner-authored editorial requests are trusted; forwarded text stays evidence.
export function splitManualText(text:string,forwarded=false){
 if(forwarded)return {text,editor_request:''};
 const marker=/(?:^|\n)\s*(?:talimat|istek|açıklamam|notum)\s*:\s*/iu.exec(text);
 if(marker)return {text:text.slice(0,marker.index).trim(),editor_request:text.slice(marker.index+marker[0].length).trim()};
 const lines=text.split('\n'),source:string[]=[],requests:string[]=[];
 for(const line of lines){
  const url=line.match(/https:\/\/[^\s<>]+/)?.[0];
  const candidate=url?line.replace(url,'').trim():line.trim();
  if(/^(?:lütfen\s+)?(?:bu(?:nu| haberi| içeriği| görseli)\s+.*(?:yaz|hazırla|oluştur|vurgula|odaklan)|(?:kısa|detaylı|sade|tek tweet|yalnızca|sadece|başlıkta|görselde|tweet(?:te|i))\b.*(?:yaz|hazırla|oluştur|göster|ver|olsun|kullan|vurgula))/iu.test(candidate)){requests.push(candidate);if(url)source.push(url);}
  else source.push(line);
 }
 return {text:source.join('\n').trim(),editor_request:requests.join('\n')};
}
