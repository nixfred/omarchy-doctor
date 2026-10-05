.pragma library

var order = {bad: 0, warn: 1, unknown: 2, ok: 3, skipped: 4}
var labels = {bad: "Problem", warn: "Attention", unknown: "Unavailable", ok: "Healthy", skipped: "Not checked"}
var domains = [
    {key: "cpu", title: "Processor", metric: "cpu_pct", unit: "%", caption: "processor activity", color: "#b6ef96", check: "cpu"},
    {key: "ram", title: "Memory", metric: "ram_available_gib", unit: "GiB", caption: "available headroom", color: "#79d4df", check: "memory"},
    {key: "disk", title: "Storage", metric: "disk_used_pct", unit: "%", caption: "root filesystem used", color: "#efbd7a", check: "storage"},
    {key: "gpu", title: "Graphics", metric: "gpu_pct", unit: "%", caption: "graphics activity", color: "#a9baf0", check: "gpu"}
]
function validRow(row) {
    return row && typeof row.id === "string" && typeof row.title === "string" && typeof row.summary === "string"
        && order[row.state] !== undefined && typeof row.domain === "string" && typeof row.metrics === "object"
}
function sorted(rows) {
    var activityOrder={recurring:0,new:1,historical:2}
    return rows.slice().sort(function(a,b) { return (a.priority === undefined ? order[a.state] : a.priority) - (b.priority === undefined ? order[b.state] : b.priority)
        || (activityOrder[a.activity]||0)-(activityOrder[b.activity]||0) || a.title.localeCompare(b.title) })
}
function findingRows(rows) {
    var out=[]
    rows.forEach(function(row) {
        if (row.findings && row.findings.length) out=out.concat(row.findings)
        else out.push(row)
    })
    return out
}
function counts(rows) {
    var result = {ok:0,warn:0,bad:0,unknown:0,skipped:0}
    rows.forEach(function(row) { if (result[row.state] !== undefined) result[row.state]++ })
    return result
}
function state(rows, complete) {
    var c = counts(rows)
    if (c.bad) return "bad"
    if (c.warn) return "warn"
    if (!complete || c.unknown || !c.ok) return "unknown"
    return "ok"
}
function domainState(rows, domain) {
    var matches = rows.filter(function(row) { return row.domain === domain })
    return state(matches, matches.length > 0)
}
function reading(metrics, key) {
    var value = metrics[key]
    if (typeof value !== "number" || !isFinite(value)) return "—"
    return value.toFixed(key.indexOf("gib") >= 0 ? 1 : 0)
}
function stamp(ts) {
    if (!ts) return "Not yet checked"
    return new Date(ts * 1000).toLocaleString()
}
function elapsed(ts, now) {
    if (!ts) return "never"
    var seconds = Math.max(0, Math.round(now - ts))
    if (seconds < 5) return "just now"
    if (seconds < 60) return seconds + "s ago"
    if (seconds < 3600) return Math.floor(seconds / 60) + "m ago"
    return Math.floor(seconds / 3600) + "h ago"
}
function mergeRows(rows, row) {
    var next = rows.filter(function(r) { return r.id !== row.id }); next.push(row); return next
}
function series(samples, key) {
    return samples.filter(function(s) { return s && s.metrics && typeof s.metrics[key] === "number" && isFinite(s.metrics[key]) })
                  .map(function(s) { return {time:s.timestamp, value:s.metrics[key]} })
}

function matches(row, filter) {
    return filter === "all" || (filter === "needs_fix" && row.needs_fix === true)
        || (filter === "investigate" && (row.state === "unknown" || (row.disposition === "investigate" && row.activity !== "historical") || row.resolution === "unverified"))
        || (filter === "recent" && row.new_count > 0) || (filter === "historical" && row.activity === "historical")
        || (filter === "attention" && (row.state === "warn" || row.state === "bad")) || row.state === filter
}
function number(row) { return row.finding_number || row.id }
function disposition(row) {
    return row.needs_fix ? "NEEDS FIXING · UNRESOLVED" : row.resolution === "verified_healthy" ? "VERIFIED HEALTHY"
        : row.disposition === "monitor" ? "MONITOR · REPAIR UNPROVEN" : row.disposition === "benign" ? "ASSESSED BENIGN"
        : "INVESTIGATE · " + (row.resolution === "unverified" ? "EVIDENCE UNAVAILABLE" : "UNRESOLVED")
}

function lastMeasuredRows(rows, scans) {
    return rows.map(function(row) {
        if (row.state !== "skipped") return row
        for (var i=0;i<scans.length;i++) {
            var measured=scans[i].rows.find(function(r){return r.id===row.id&&r.state!=="skipped"})
            if (!measured) continue
            if (measured.state!=="warn"&&measured.state!=="bad")return row
            var copy={};for(var key in measured)copy[key]=measured[key]
            copy.coverage_note="Not checked in the latest scan. This is the last measured warning, from "+stamp(measured.timestamp)+"."
            return copy
        }
        return row
    })
}
function fixLabel(status) {
    var names={fixed:"Doctor verified healthy",pending:"Waiting for agent",still_failing:"Doctor still sees a warning",regressed:"Warning returned",reviewed_unproven:"Agent finished · repair unproven",blocked:"Agent needs help",failed:"Agent could not finish",interrupted:"Agent interrupted",no_result:"No result returned",launch_failed:"Agent did not start",superseded:"Earlier attempt"}
    return names[status]||status
}

function presentation(rows, complete, stale) {
    var fs=findingRows(rows), needs=fs.filter(function(f){return f.needs_fix===true || (f.needs_fix===undefined&&!f.activity&&(f.state==="bad"||f.state==="warn"))})
    var unavailable=fs.filter(function(f){return f.state==="unknown"}), history=fs.filter(function(f){return f.activity==="historical"})
    var review=fs.filter(function(f){return f.disposition==="investigate"||f.resolution==="unverified"})
    var oldReview=history.filter(function(f){return f.disposition!=="monitor"&&f.disposition!=="benign"})
    var unconfirmed=fs.filter(function(f){return !f.activity&&!f.findings&&(f.state==="warn"||f.state==="bad")&&f.needs_fix===false})
    var recentReview=fs.filter(function(f){return f.new_count>0&&!f.needs_fix&&f.disposition!=="monitor"&&f.disposition!=="benign"})
    var state=needs.some(function(f){return f.state==="bad"})?"bad":needs.length?"warn":!complete||stale||unavailable.length||oldReview.length||recentReview.length||unconfirmed.length?"unknown":"ok"
    return {state:state,needs:needs.length,unavailable:unavailable.length,historical:history.length,review:review.length,oldReview:oldReview.length,unconfirmed:unconfirmed.length,recentReview:recentReview.length,badge:needs.length+unavailable.length+recentReview.length}
}
