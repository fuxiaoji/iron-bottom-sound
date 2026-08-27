import {Fragment,useEffect,useMemo,useState} from "react";
import type {ReactNode} from "react";
import {realisticCommandRules} from "./api";

type Props={onClose:()=>void};

function inline(text:string):ReactNode[]{
 return text.split(/(`[^`]+`)/g).filter(Boolean).map((part,index)=>
  part.startsWith("`")&&part.endsWith("`")?<code key={index}>{part.slice(1,-1)}</code>:<Fragment key={index}>{part}</Fragment>
 );
}

function slug(text:string,index:number){return `rule-${index}-${text.replace(/[\s（）()：:、“”]/g,"-").replace(/-+/g,"-")}`}

function renderMarkdown(source:string){
 const lines=source.split(/\r?\n/);const nodes:ReactNode[]=[];let index=0;
 while(index<lines.length){
  const line=lines[index].trim();
  if(!line){index++;continue}
  const heading=line.match(/^(#{1,3})\s+(.+)$/);
  if(heading){const level=heading[1].length;const id=slug(heading[2],index);nodes.push(level===1?<h1 id={id} key={index}>{inline(heading[2])}</h1>:level===2?<h2 id={id} key={index}>{inline(heading[2])}</h2>:<h3 id={id} key={index}>{inline(heading[2])}</h3>);index++;continue}
  if(line.startsWith("> ")){nodes.push(<blockquote key={index}>{inline(line.slice(2))}</blockquote>);index++;continue}
  if(/^[-*]\s+/.test(line)){const items:ReactNode[]=[];while(index<lines.length&&/^[-*]\s+/.test(lines[index].trim())){items.push(<li key={index}>{inline(lines[index].trim().replace(/^[-*]\s+/,""))}</li>);index++}nodes.push(<ul key={`u-${index}`}>{items}</ul>);continue}
  if(/^\d+\.\s+/.test(line)){const items:ReactNode[]=[];while(index<lines.length&&/^\d+\.\s+/.test(lines[index].trim())){items.push(<li key={index}>{inline(lines[index].trim().replace(/^\d+\.\s+/,""))}</li>);index++}nodes.push(<ol key={`o-${index}`}>{items}</ol>);continue}
  const paragraph=[line];index++;while(index<lines.length&&lines[index].trim()&&!/^(#{1,3})\s+|^[-*]\s+|^\d+\.\s+|^>\s+/.test(lines[index].trim())){paragraph.push(lines[index].trim());index++}nodes.push(<p key={`p-${index}`}>{inline(paragraph.join(" "))}</p>);
 }
 return nodes;
}

export function RealisticRulesModal({onClose}:Props){
 const [source,setSource]=useState("");const [error,setError]=useState("");
 useEffect(()=>{let active=true;realisticCommandRules().then(text=>{if(active)setSource(text)}).catch(reason=>{if(active)setError(String(reason))});return()=>{active=false}},[]);
 useEffect(()=>{const close=(event:KeyboardEvent)=>{if(event.key==="Escape")onClose()};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close)},[onClose]);
 const headings=useMemo(()=>source.split(/\r?\n/).map((line,index)=>({match:line.match(/^##\s+(.+)$/),index})).filter(item=>item.match).map(item=>({title:item.match![1],id:slug(item.match![1],item.index)})),[source]);
 return <div className="rules-modal-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}><section className="rules-modal" role="dialog" aria-modal="true" aria-labelledby="realistic-rules-title">
  <header><div><span>IBS-R-RC · 玩家规则书</span><h2 id="realistic-rules-title">真实模式完整规则</h2></div><div className="rules-modal-actions"><button type="button" onClick={()=>window.print()}>打印</button><button type="button" onClick={onClose} aria-label="关闭规则预览">关闭</button></div></header>
  <div className="rules-modal-layout"><nav aria-label="规则目录"><b>目录</b>{headings.map(item=><a key={item.id} href={`#${item.id}`}>{item.title}</a>)}</nav><article className="rules-markdown">{error?<p className="rules-load-error">规则加载失败：{error}</p>:source?renderMarkdown(source):<p>正在载入经过审计的规则正文……</p>}</article></div>
 </section></div>;
}
