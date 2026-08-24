export function counterAssetUrl(asset:string|null){
 return asset?`/assets/counters/${encodeURIComponent(asset)}`:"";
}
