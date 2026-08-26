// 兵棋棋子图片：跟随后端静态挂载点 /assets/counters，前缀随 Vite base（/tiedi 部署
// 时构建带 --base=/tiedi/，自动变成 /tiedi/assets/counters/...）。
export function counterAssetUrl(asset:string|null){
 return asset?`${import.meta.env.BASE_URL}assets/counters/${encodeURIComponent(asset)}`:"";
}
