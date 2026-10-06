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
        if(row.findings&&row.findings.length&&(row.limited||row.coverage_incomplete||row.state==="unknown")){var coverage={};for(var key in row)coverage[key]=row[key];coverage.state="unknown";coverage.resolution="unverified";coverage.disposition="investigate";coverage.needs_fix=false;coverage.evidence_kind="coverage";out.push(coverage)}
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
function domainState(rows, domain, now) {
    var matches = rows.filter(function(row) { return row.domain === domain })
    return indicator(matches,matches.length>0,false,false,now||Date.now()/1000).state
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

function quietNote(row){return !!(row.evidence_kind==="log_warning"||row.evidence_kind==="test_event"||row.activity&&(row.check_id==="shell"||row.check_id==="journal"))}
function oldMeasurement(row,now){return !!now&&!!row.timestamp&&now-row.timestamp>600}
function actionable(row,now){return (row.needs_fix===true||row.needs_fix===undefined&&!row.activity&&(row.state==="warn"||row.state==="bad"))&&!oldMeasurement(row,now)}
function matches(row,filter,now) {
    return filter==="all" || filter==="needs_fix"&&(now?actionable(row,now):row.needs_fix===true)
        || filter==="notes"&&quietNote(row)&&!row.needs_fix
        || filter==="investigate"&&(row.state==="unknown"||row.resolution==="unverified"||oldMeasurement(row,now)&&row.needs_fix||row.disposition==="investigate"&&row.activity!=="historical"&&!quietNote(row))
        || filter==="recent"&&row.new_count>0 || filter==="historical"&&(row.activity==="historical"||oldMeasurement(row,now)||!!row.recovery)
        || filter==="attention"&&(row.state==="warn"||row.state==="bad") || row.state===filter
}

function number(row) { return row.finding_number || row.id }
function disposition(row,now) {
    if(row.needs_fix)return row.activity!=="historical"&&now&&row.timestamp&&now-row.timestamp>600?"SAVED WARNING · RECHECK CURRENT STATE":"STILL NEEDS ACTION"
    if(row.evidence_kind==="coverage")return "LOG REVIEW INCOMPLETE · NO REPAIR ESTABLISHED"
    if(row.evidence_kind==="test_event")return "TEST INVOCATION · KEPT IN HISTORY"
    if(quietNote(row))return row.activity==="historical"?"PAST LOG WARNING · REPAIR NOT ESTABLISHED":"LOG WARNING · FUNCTIONAL IMPACT NOT ESTABLISHED"
    if(row.activity==="historical")return row.disposition==="benign"?"PAST EVENT · ASSESSED BENIGN":row.disposition==="monitor"?"PAST EVENT · MONITORED · NO VERIFIED REPAIR":"PAST EVENT · NOT REVIEWED"
    if(row.resolution==="verified_healthy")return row.recovery&&row.recovery.kind==="without_handoff"?"RECOVERED WITHOUT A DOCTOR HANDOFF · MEASURED HEALTHY":"MEASURED HEALTHY"
    if(row.state==="unknown"||row.resolution==="unverified")return "NEEDS VERIFICATION · COVERAGE INCOMPLETE"
    if(row.state==="skipped")return "NOT CHECKED IN THIS SCAN"
    return row.disposition==="benign"?"ASSESSED BENIGN":row.disposition==="monitor"?"MONITORED · NO VERIFIED REPAIR":"NOT REVIEWED · NO VERIFIED REPAIR"
}

function lastMeasuredRows(rows, scans) {
    return rows.map(function(row) {
        if (row.state !== "skipped") return row
        for (var i=0;i<scans.length;i++) {
            var measured=scans[i].rows.find(function(r){return r.id===row.id&&r.state!=="skipped"})
            if (!measured) continue
            if (measured.state!=="warn"&&measured.state!=="bad"&&measured.state!=="unknown")return row
            var copy={};for(var key in measured)copy[key]=measured[key]
            copy.coverage_note="Not checked in the latest scan. This is the last measured "+labels[measured.state].toLowerCase()+" result, from "+stamp(measured.timestamp)+". "+(measured.coverage_note||"")
            return copy
        }
        return row
    })
}
function fixLabel(status) {
    var names={fixed:"Doctor verified healthy · cause unproven",pending:"Waiting for agent",still_failing:"Doctor still sees a warning",regressed:"Warning returned",reviewed_unproven:"Agent finished · repair unproven",blocked:"Agent needs help",failed:"Agent could not finish",interrupted:"Agent interrupted",no_result:"No result returned",launch_failed:"Agent did not start",superseded:"Earlier attempt"}
    return names[status]||status
}

function presentation(rows,complete,stale,now) {
    var fs=findingRows(rows), needs=fs.filter(function(f){return actionable(f,now)})
    var unavailable=fs.filter(function(f){return f.state==="unknown"||f.resolution==="unverified"}),history=fs.filter(function(f){return f.activity==="historical"||oldMeasurement(f,now)||f.recovery})
    var notes=fs.filter(function(f){return quietNote(f)&&!f.needs_fix}),review=fs.filter(function(f){return f.disposition==="investigate"||f.resolution==="unverified"})
    var recentReview=fs.filter(function(f){return f.new_count>0&&!f.needs_fix&&!quietNote(f)&&f.disposition!=="monitor"&&f.disposition!=="benign"&&!oldMeasurement(f,now)})
    return {state:needs.some(function(f){return f.state==="bad"})?"bad":needs.length?"warn":!complete||stale||unavailable.length||recentReview.length?"unknown":"ok",needs:needs.length,unavailable:unavailable.length,historical:history.length,review:review.length,oldReview:history.filter(function(f){return f.disposition==="investigate"}).length,unconfirmed:0,recentReview:recentReview.length,logNotes:notes.length,badge:needs.length}
}

// Handoff observations describe transport and evidence, never imagined agent activity.
function workActive(f, now) {
    if (!f || (f.report && f.report.outcome)) return false
    return f.phase === "running" && f.supervisor_alive === true
        || f.phase === "prepared" && now - f.started < 30
}
function workState(f, now) {
    if (!f) return {key:"unknown",title:"Progress unavailable",detail:"Reload the saved handoff before starting another attempt."}
    if (f.phase === "preparing") return {key:"preparing",title:"Hang on — handing this to your agent…",detail:"Doctor is preparing the handoff. You can return to the app at any time."}
    if (f.launch_error) return {key:"launch_failed",title:(f.agent||"Agent")+" could not start for "+(f.finding_number||f.check),detail:f.title+" · "+f.launch_error}
    if (f.error) return {key:"launch_failed",title:"The handoff could not start",detail:f.error}
    var report = f.report && f.report.outcome
    if (report && !f.verified && f.status!=="superseded" && f.status!=="regressed" && !(f.verifications || []).some(function(v){return v.timestamp >= (f.report_received_at||0)})) return {key:"verifying",title:"Report received — verification pending",detail:"The agent's report is saved. Doctor has not yet independently verified the result."}
    if (f.verified) return {key:"fixed",title:"Doctor verified this check healthy",detail:"The independent check passed. Its command, time and evidence are saved below."}
    if (f.status === "regressed") return {key:"regressed",title:"The warning returned",detail:"A later Doctor check found the concern again. Earlier reports and checks remain saved."}
    if (report) return {key:f.status,title:fixLabel(f.status),detail:"The report returned. This repair is unproven; review Doctor's independent evidence below."}
    if (f.phase === "running" && f.supervisor_alive === true) {
        if (!f.observed_at || now-f.observed_at>20) return {key:"unknown",title:"Progress needs a fresh check",detail:"The last saved observation saw the launcher running. Refresh progress to check again; current agent activity is unknown."}
        var waiting = now - f.started >= 600
        return {key:waiting?"waiting":"running",title:waiting?"Still waiting — agent activity unknown":"Hang on — waiting for "+(f.agent || "your agent"),detail:f.launch_mode==="background"?"The background launcher is running. Only received agent events are shown below. No completion receipt has returned.":"The launcher is still running. No completion report has returned. Doctor cannot see the agent's individual steps."}
    }
    if (f.phase === "prepared" && now - f.started < 30) return {key:"preparing",title:"Preparing the agent handoff…",detail:"The saved attempt is waiting for its launcher. No repair is proven."}
    var titles={launch_failed:"The agent could not start",interrupted:"The launcher was interrupted",no_result:"No completion report returned",superseded:"This is an earlier attempt"}
    return {key:titles[f.status]?f.status:"unknown",title:titles[f.status] || "Agent progress is unknown",detail:"No completion report is available. The agent may still be working elsewhere. Recheck the finding and inspect this attempt before deciding to hand it off again."}
}
function workDuration(f, now) {
    if (!f || !f.started) return "—"
    var end = f.ended || (f.report && f.report.outcome ? f.last_update : 0) || (f.verified ? f.resolved : 0) || now
    var seconds = Math.max(0, Math.floor(end-f.started))
    return seconds < 60 ? seconds+"s" : seconds < 3600 ? Math.floor(seconds/60)+"m "+seconds%60+"s" : Math.floor(seconds/3600)+"h "+Math.floor(seconds%3600/60)+"m"
}

function indicator(rows,complete,stale,scanning,now) {
    var fs=findingRows(rows), faults=sorted(fs.filter(function(r){return actionable(r,now)}))
    var coverage=sorted(fs.filter(function(r){return r.state==="unknown"||r.resolution==="unverified"}))
    var review=sorted(fs.filter(function(r){return !r.needs_fix&&!quietNote(r)&&r.activity!=="historical"&&r.new_count>0&&!oldMeasurement(r,now)&&(!r.last_seen||now-r.last_seen<=600)&&r.disposition!=="monitor"&&r.disposition!=="benign"}))
    var metadata={actionable:faults.length,coverage:coverage.length,review:review.length,badge:faults.length}
    function verdict(state,label,reason,target,filter){return {state:state,label:label,reason:reason,target:target,filter:filter,badge:metadata.badge,actionable:metadata.actionable,coverage:metadata.coverage,review:metadata.review}}
    var major=faults.find(function(r){return r.state==="bad"||r.severity==="critical"||r.severity==="high"})
    if(major)return verdict("bad","Red · current actionable fault",number(major)+" · "+major.title+": "+major.summary,major,"needs_fix")
    if(faults.length)return verdict("warn","Yellow · current actionable warning",number(faults[0])+" · "+faults[0].title+": "+faults[0].summary,faults[0],"needs_fix")
    if(coverage.length)return verdict("unknown","Gray · coverage incomplete","Health is not verified yet. "+coverage.length+" check(s) incomplete. "+coverage.map(function(r){return number(r)+" · "+r.title+": "+r.summary+(oldMeasurement(r,now)?" Last measurement is old; recheck for current evidence.":"")}).join("\n"),coverage[0],"investigate")
    if(review.length)return verdict("unknown","Gray · event review","No repair is established. "+review.length+" current event record(s) need review; a recorded crash is not proof the process is still failing.",review[0],"investigate")
    if(scanning||!complete)return verdict("unknown","Gray · checks unfinished",scanning?"Doctor is checking. Healthy coverage is not yet established.":"The saved checkup is incomplete. Run Doctor for current evidence.",null,"investigate")
    if(stale)return verdict("unknown","Gray · checkup is old","The last complete checkup is over ten minutes old. Run Doctor for current evidence.",null,"investigate")
    var old=sorted(fs.filter(function(r){return !r.activity&&oldMeasurement(r,now)&&r.state!=="skipped"}))[0]
    if(old)return verdict("unknown","Gray · measurement is old",number(old)+" · "+old.title+" needs a fresh measurement; a saved warning is not a current diagnosis.",old,"investigate")
    if(!fs.some(function(r){return r.state==="ok"&&!r.activity}))return verdict("unknown","Gray · no healthy measurement","No supported check has a fresh healthy measurement yet. Run Doctor.",null,"investigate")
    return verdict("ok","Green · checked scope healthy","No known actionable problems in checked scope. Completed supported checks are fresh. Optional skipped checks, log notes and past events remain visible.",null,"all")
}

function healthHeadline(verdict,scanning,hasRows) {
    if(scanning)return "Checking your desktop…"
    if(!hasRows)return "Health is not verified yet."
    if(verdict.state==="bad"||verdict.state==="warn")return "Let's look at "+verdict.actionable+" actionable concern(s)."
    if(verdict.state==="ok")return "Checked scope is healthy."
    if(verdict.coverage)return verdict.coverage+(verdict.coverage===1?" check still needs verification.":" checks still need verification.")
    if(verdict.review)return verdict.review+(verdict.review===1?" event record needs review.":" event records need review.")
    return "Health is not verified yet."
}

function issueSummary(rows,complete,archived,now) {
    var fs=findingRows(rows||[]),needs=fs.filter(function(r){return archived?r.needs_fix===true:actionable(r,now)}).length
    var gaps=fs.filter(function(r){return r.state==="unknown"||r.resolution==="unverified"}).length
    var old=!!now&&fs.some(function(r){return !r.activity&&r.timestamp&&now-r.timestamp>600&&r.state!=="skipped"})
    var scope=archived?"At this saved checkup: ":old?"Measurements are old; run Doctor for current evidence. Last saved checkup: ":""
    if(!complete&&!archived)return "Checks are unfinished. Run Doctor before deciding whether a repair is needed."
    if(gaps&&!needs&&!archived)return scope+"Health is not verified: "+gaps+(gaps===1?" check needs verification.":" checks need verification.")+" Open Verification to finish coverage. No actionable repairs were identified in completed checks; Issues retains the evidence."
    return scope+(needs?needs+(archived||old?(needs===1?" finding needed attention.":" findings needed attention."):(needs===1?" finding still needs action.":" findings still need action.")):archived||old?"No repairs were identified.":"No known actionable problems in checked scope.")+(gaps?" "+gaps+(gaps===1?" check needs verification.":" checks need verification.")+" Open Verification to finish coverage; Issues retains the evidence.":" Completed supported checks have no reported coverage gaps. Log notes and past events remain visible.")
}
function nextAction(row) {
    if(!row)return "Run Doctor to collect a current measurement."
    if(row.id==="packages"&&row.state==="unknown")return "Open Verification → Verify protected package files. Review the fixed read-only command and authenticate in its normal terminal. An ordinary recheck cannot establish protected-file coverage."
    if(quietNote(row))return "This log warning or test record is preserved. Review its source, time and functional impact before marking any repair needed; recurrence alone does not prove an ongoing failure."
    if((row.id==="shell"||row.id==="journal")&&row.state==="unknown")return "Open Verification → Read complete shell/boot journal. Each bounded operation advances the same fixed snapshot; Continue collection resumes its saved cursor. Only confirmed complete readable coverage can clear this gap."
    if(row.state==="unknown")return "Recheck this finding for a valid current measurement, then inspect any remaining access or coverage limitation."
    if(row.activity==="historical"&&!row.needs_fix)return "This is a past event awaiting review. Keep its evidence; mark a diagnosis only when supported. It does not automatically require a repair."
    return row.needs_fix?"Inspect the evidence and diagnose the cause before deciding on a repair.":"Review the saved measurement and history."
}
