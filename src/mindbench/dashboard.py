"""Self-contained offline benchmark QA dashboard without third-party scripts."""
from __future__ import annotations

from html import escape
import json
from typing import Any


def benchmark_html(report: dict[str, Any]) -> str:
    title = "Multimodal MindBench | Reproducibility Explorer"
    safe = json.dumps(report, sort_keys=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>''' + escape(title) + '''</title><style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,sans-serif;color:#eaf0f8;background:#0b1422}
*{box-sizing:border-box}body{margin:0;line-height:1.55}a{color:#85d9ff}a:focus-visible,button:focus-visible,select:focus-visible{outline:3px solid #f7c66a;outline-offset:3px}
.skip{position:absolute;left:-10000px}.skip:focus{left:1rem;top:1rem;background:#0b1422;padding:.5rem;z-index:4}
header{padding:2rem max(1rem,calc((100vw - 1100px)/2));background:linear-gradient(120deg,#162f4c,#0b1422)}
h1{font-size:clamp(1.6rem,4vw,2.8rem);line-height:1.15;margin:.5rem 0}h2{font-size:1.3rem}p{max-width:74ch}
main{max-width:1100px;margin:auto;padding:1rem}nav a{margin-right:1.5rem}nav{padding-bottom:1rem}
.warning{border-left:4px solid #f7c66a;background:#2c2417;padding:.75rem 1rem;margin:1rem 0}
.controls{display:flex;flex-wrap:wrap;gap:1rem;margin:1.5rem 0}label{display:grid;gap:.3rem}select,button{color:inherit;background:#192e44;border:1px solid #a3b8c9;border-radius:.5rem;padding:.7rem;font:inherit;min-height:44px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}
.card{background:#15273a;border:1px solid #486075;border-radius:1rem;padding:1rem}
.metric{font-size:2rem;font-variant-numeric:tabular-nums;margin:.4rem 0}.hint{color:#c2cedc;font-size:.9rem}
.bars{display:grid;gap:.7rem;padding:1rem 0}.barrow{display:grid;grid-template-columns:130px 1fr 60px;gap:.75rem;align-items:center}
.track{border:1px solid #93a7b8;border-radius:1rem;height:1.3rem;background:#243b52;overflow:hidden}.fill{height:100%;background:#8bdac8}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:.65rem .5rem;border-bottom:1px solid #52697b}td{text-align:right;font-variant-numeric:tabular-nums}
.tablewrap{overflow-x:auto}footer{padding:2rem 0;color:#b8cbdc}li{margin:.3rem 0}
@media(max-width:580px){.barrow{grid-template-columns:92px 1fr 50px;gap:.3rem;font-size:.8rem}header{padding:1rem}main{padding:.8rem}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;transition:none!important}}
</style></head><body><a class="skip" href="#main">Skip to results</a><header><p>NONCLINICAL RESEARCH SOFTWARE · SYNTHETIC-ONLY DEMO</p>
<h1>Multimodal MindBench</h1><p>Browse group-disjoint unimodal and fusion benchmarks with visible limitations, sample counts, subject bootstraps, and reproducibility metadata. No medical or real-person conclusions.</p>
<nav aria-label="Sections"><a href="#results">Models</a><a href="#splits">Split audit</a><a href="#limitations">Limitations</a></nav></header>
<main id="main"><div class="warning" role="note"><strong>Simulated evidence only.</strong> Feature vectors are invented by software, not measured EEG or behavior. Accuracy bars are pipeline tests, not neurophysiological findings.</div>
<section aria-labelledby="results-heading" id="results"><h2 id="results-heading">Benchmark comparisons</h2>
<div class="controls"><label for="metric">Evaluation metric<select id="metric"><option value="accuracy">Accuracy</option><option value="balanced_accuracy">Balanced accuracy</option><option value="roc_auc">ROC AUC</option><option value="brier">Brier score (lower is better)</option><option value="ece10">ECE-10 (lower is better)</option></select></label>
<label for="scope">Analysis population<select id="scope"><option value="complete">Identical complete-case test rows</option><option value="available">Include missing-input fallback</option></select></label></div>
<div class="grid" id="cards" aria-live="polite"></div><h3>Metric comparison</h3><div class="bars" id="bars" role="img" aria-label="Model metrics; numerical values also in the table below"></div>
<div class="tablewrap"><table><caption>Exact metrics and number of test examples</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Test n</th><th scope="col">Metric</th><th scope="col">Accuracy 95% cluster interval</th></tr></thead><tbody id="metrics"></tbody></table></div></section>
<section id="splits"><h2>Subject isolation and reproducibility</h2><div id="audit" class="grid"></div><p><a id="download" download="mindbench-benchmark.json" href="#">Download complete benchmark JSON</a></p></section>
<section id="limitations"><h2>Limitations and scientific integrity</h2><ul id="limitations-list"></ul></section>
<footer>Self-contained, keyboard navigable, no telemetry, no live data upload or backend. Built for scientific evaluation review, not release.</footer></main>
<script id="report-data" type="application/json">''' + safe + '''</script><script>
"use strict";
const report=JSON.parse(document.getElementById("report-data").textContent);
const names={eeg:"EEG only",behavior:"Behavior only",early_fusion:"Early fusion",late_fusion:"Late fusion",late_fusion_available_modality:"Late fusion + fallback"};
const escapeHtml=(value)=>String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const metric=document.getElementById("metric"),scope=document.getElementById("scope");
function draw(){
const metricName=metric.value;
const keys=scope.value==="complete"?["eeg","behavior","early_fusion","late_fusion"]:["late_fusion_available_modality"];
let cards="", bars="", rows="";
for(const key of keys){const data=report.results[key];const value=data[metricName];const printable=value===null?"N/A":Number(value).toFixed(3);
const interval=data.accuracy_subject_bootstrap_95pct;
const ci=interval?interval.map(x=>Number(x).toFixed(3)).join(" to "):"Not computed (different denominator)";
cards+=`<article class="card"><h3>${escapeHtml(names[key])}</h3><p class="metric">${escapeHtml(printable)}</p><p class="hint">${escapeHtml(metricName)} · ${data.n} held-out trials</p></article>`;
const width=value===null?0:Math.max(0,Math.min(100,Number(value)*100));
bars+=`<div class="barrow"><span>${escapeHtml(names[key])}</span><div class="track"><div class="fill" style="width:${width}%"></div></div><span>${escapeHtml(printable)}</span></div>`;
rows+=`<tr><th scope="row">${escapeHtml(names[key])}</th><td>${data.n}</td><td>${escapeHtml(printable)}</td><td>${escapeHtml(ci)}</td></tr>`;
}
document.getElementById("cards").innerHTML=cards;
document.getElementById("bars").innerHTML=bars;
document.getElementById("metrics").innerHTML=rows;
}
metric.addEventListener("change",draw);scope.addEventListener("change",draw);draw();
document.getElementById("audit").innerHTML=Object.entries(report.subjects).map(([name,values])=>`<article class="card"><h3>${escapeHtml(name)} subjects</h3><p class="metric">${values.length}</p><p class="hint">Disjoint anonymized simulated groups</p></article>`).join("")+
`<article class="card"><h3>Dataset fingerprint</h3><p class="hint" style="overflow-wrap:anywhere">${escapeHtml(report.cohort_digest_sha256)}</p><p>Random seed: ${Number(report.seed)}</p></article>`;
document.getElementById("limitations-list").innerHTML=report.limitations.map(x=>`<li>${escapeHtml(x)}</li>`).join("");
const blob=new Blob([JSON.stringify(report,null,2)],{type:"application/json"});document.getElementById("download").href=URL.createObjectURL(blob);
</script></body></html>'''
