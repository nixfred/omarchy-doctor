import QtQuick
import qs.Commons
import "Model.js" as Model

Column {
    id: pane
    objectName: "doctor-verification-pane"
    property var host
    spacing: 14
    function row(check){return host.shownRows.find(function(r){return r.id===check})||null}
    function done(check){var r=row(check);return !!r&&!Model.oldMeasurement(r,host.now)&&(check!=="packages"?!!r.coverage&&(r.coverage.complete===true||r.coverage.complete===undefined&&r.limited===false&&r.state!=="unknown"):!!r.metrics&&r.metrics.integrity_complete===true)}
    function busy(job){return !!job&&(job.phase==="awaiting_auth"||job.phase==="verifying")&&host.now-job.updated<180}
    Text {textFormat:Text.PlainText;width:parent.width;text:"Finish verification";color:host.ink;font.family:Style.font.family;font.pixelSize:24;font.bold:true}
    Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:"Green means fresh completed checks with no known actionable faults. Finish the incomplete checks below; warning notes and history remain visible. These actions measure the system. They do not repair it.";color:host.dim;font.family:Style.font.family;font.pixelSize:14}
    Repeater {
        model:[{check:"journal",name:"Complete boot log coverage"},{check:"shell",name:"Complete shell log coverage"},{check:"packages",name:"Verify protected package files"}].filter(function(item){var measured=pane.row(item.check);return item.check!=="packages"||!!host.verificationJob(item.check)||!!measured&&measured.state==="unknown"})
        Rectangle {
            id: card
            width:pane.width;height:body.implicitHeight+32;radius:12;color:host.card;border.color:host.edge
            property string check:modelData.check
            property var job:host.verificationJob(check)
            property var measured:pane.row(check)
            property bool verified:pane.done(check)
            Column {
                id:body;x:16;y:16;width:parent.width-32;spacing:10
                Text {objectName:"doctor-"+card.check+"-heading";textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:(card.measured?Model.number(card.measured):"Not measured")+" · "+modelData.name;color:host.ink;font.family:Style.font.family;font.pixelSize:17;font.bold:true}
                Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:card.verified?(card.measured&&card.measured.needs_fix?"Verification completed; an actual fault remains. Open its evidence to diagnose the next action.":"Completed and fresh. Evidence remains available."):card.check==="packages"&&card.measured&&card.measured.verification_expired?"The previous privileged measurement is old or packages changed. Authenticate for a fresh protected-file measurement; an ordinary recheck cannot renew that evidence.":card.check==="journal"?"Boot-log coverage is not complete. Read the full available current-boot/seven-day priority 0–3 snapshot with all field contents in cursor pages. Existing benign-note and crash-duplicate rules stay unchanged. Any remaining invalid or unreadable record prevents completion.":card.check==="shell"?"The ordinary read stops at 500 entries. It cannot establish full coverage while more logs exist. This action reads the same available user journal from this boot, within seven days, through a fixed end time. Cursor pages continue until the end is confirmed.":"The last ordinary check could not read protected paths. Repeating it cannot finish verification. Use the read-only privileged check below; only pacman gets root, and you authenticate in the normal terminal.";color:card.verified?host.good:host.dim;font.family:Style.font.family;font.pixelSize:14}
                Text {textFormat:Text.PlainText;objectName:card.check==="journal"?"doctor-journal-progress":card.check==="shell"?"doctor-shell-progress":"doctor-package-progress";width:parent.width;wrapMode:Text.WordWrap;color:host.ink;font.family:Style.font.family;font.pixelSize:13;text:!card.job?"Not started.":card.check!=="packages"?(card.job.raw_entries||0)+" entries read in "+(card.job.pages||0)+" pages · "+card.job.phase+(card.job.until?" · snapshot ends "+Model.stamp(card.job.until):"")+(card.job.error?"\n"+card.job.error:""):card.job.phase==="awaiting_auth"||card.job.phase==="verifying"?(pane.busy(card.job)?"Use the verification terminal to authenticate. Ctrl+C cancels. Doctor awaits a measured result.":"The last terminal observation is old. Close or inspect that terminal before starting again."):card.job.phase+(card.job.error?" · "+card.job.error:"")}
                Text {textFormat:Text.PlainText;visible:card.check==="packages";width:parent.width;wrapMode:Text.WordWrap;text:"sudo /usr/bin/pacman -Qk\nChecks file existence. No install, removal, permission change, or agent launch.";color:host.dim;font.family:Style.font.family;font.pixelSize:13}
                Flow {width:parent.width;spacing:8
                    DoctorAction {objectName:card.check==="journal"?"doctor-verify-journal":card.check==="shell"?"doctor-verify-shell":"doctor-verify-packages";text:card.check!=="packages"?(card.job&&card.job.requires_restart?"Restart collection":card.job&&card.job.phase!=="complete"?"Continue collection":(card.check==="shell"?"Read complete shell journal":"Read complete boot journal")):"Verify protected package files";primary:!card.verified;ink:host.ink;accent:host.good;enabled:!host.scanning&&!host.verifying&&(card.check!=="packages"||!pane.busy(card.job));onClicked:{if(card.check==="shell")host.verifyShell(!!card.job&&card.job.requires_restart===true);else if(card.check==="journal")host.verifyJournal(!!card.job&&card.job.requires_restart===true);else host.requestPackageVerification()}}
                    DoctorAction {visible:card.check===host.verificationCheck&&host.verifying;objectName:"doctor-cancel-shell-verification";text:"Cancel collection";ink:host.ink;onClicked:host.cancelVerification()}
                    DoctorAction {visible:card.check!=="packages"&&!!card.job&&!host.verifying;objectName:"doctor-restart-shell-verification";text:"Restart snapshot";ink:host.ink;enabled:!host.scanning;onClicked:{if(card.check==="shell")host.verifyShell(true);else host.verifyJournal(true)}}
                    DoctorAction {text:"View evidence";ink:host.ink;onClicked:host.showFindings(card.check)}
                }
            }
        }
    }
    Repeater {
        model:host.shownRows.filter(function(r){return r.id!=="shell"&&r.id!=="packages"&&r.id!=="journal"&&r.id!=="drives"&&(r.state==="unknown"||r.state!=="skipped"&&!r.activity&&Model.oldMeasurement(r,host.now))})
        Rectangle {width:pane.width;height:other.implicitHeight+28;radius:12;color:host.card;border.color:host.edge
            Column {id:other;x:14;y:14;width:parent.width-28;spacing:8
                Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:Model.number(modelData)+" · "+modelData.title;color:host.ink;font.family:Style.font.family;font.pixelSize:16;font.bold:true}
                Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:modelData.summary+(modelData.limited?" This collector reached its documented limit; repeating the same bounded query cannot establish complete coverage.":Model.oldMeasurement(modelData,host.now)?" This measurement is over ten minutes old.":" Recheck when its command/data source is available; incomplete evidence cannot establish healthy coverage.");color:host.dim;font.family:Style.font.family;font.pixelSize:13}
                Flow {width:parent.width;spacing:8
                    DoctorAction {text:"Measure again";visible:!modelData.limited;ink:host.ink;enabled:!host.scanning&&!host.verifying;onClicked:host.recheck(modelData.id)}
                    DoctorAction {text:"View evidence and source";ink:host.ink;onClicked:host.showFindings(modelData.id)}
                }
            }
        }
    }
    Rectangle {
        id: driveCard
        property var measured:pane.row("drives")
        property var job:host.verificationJob("drives")
        property bool verified:!!measured&&!Model.oldMeasurement(measured,host.now)&&(!!measured.metrics&&measured.metrics.smart_complete===true||measured.state!=="unknown"&&!measured.coverage_incomplete)
        visible:!!measured&&measured.state!=="skipped"||!!job
        width:pane.width;height:driveBody.implicitHeight+32;radius:12;color:host.card;border.color:host.edge
        Column {id:driveBody;x:16;y:16;width:parent.width-32;spacing:10
            Text {objectName:"doctor-drives-heading";textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:(driveCard.measured?Model.number(driveCard.measured):"Not measured")+" · Read physical drive SMART health";color:host.ink;font.family:Style.font.family;font.pixelSize:17;font.bold:true}
            Text {objectName:"doctor-smart-explanation";textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:driveCard.verified?(driveCard.measured.state==="bad"?"SMART measured an actual drive fault. Open its evidence; authenticating again does not repair it.":"Completed and fresh. Evidence retains its original measurement time."):"An ordinary retry cannot finish inaccessible or old SMART coverage. Review the discovered devices and exact read-only commands below, then authenticate in the normal terminal. Only packaged smartctl gets root; Doctor stays unprivileged. No tests, writes, firmware or permissions change.";color:driveCard.verified&&driveCard.measured.state!=="bad"?host.good:host.dim;font.family:Style.font.family;font.pixelSize:14}
            Text {objectName:"doctor-smart-progress";textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:!driveCard.job?"Not started.":pane.busy(driveCard.job)?"Use the SMART verification terminal to authenticate. Ctrl+C cancels; Doctor awaits measured evidence.":driveCard.job.phase+(driveCard.job.error?" · "+driveCard.job.error:"");color:host.ink;font.family:Style.font.family;font.pixelSize:13}
            Flow {width:parent.width;spacing:8
                DoctorAction {objectName:"doctor-verify-smart";text:"Read SMART health";primary:!driveCard.verified;ink:host.ink;accent:host.good;enabled:!host.scanning&&!host.verifying&&!pane.busy(driveCard.job)&&!host.smartPlanBusy;onClicked:host.requestSmartVerification()}
                DoctorAction {text:"View evidence";ink:host.ink;onClicked:host.showFindings("drives")}
            }
        }
    }
    Rectangle {visible:host.smartConfirmation;width:parent.width;height:smartApproval.implicitHeight+32;radius:12;color:host.card;border.color:host.warning
        Column {id:smartApproval;x:16;y:16;width:parent.width-32;spacing:10
            Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:"Read SMART health on these devices? The normal terminal handles authentication. Device identity is checked before and after measurement.";color:host.ink;font.family:Style.font.family;font.pixelSize:14}
            Text {objectName:"doctor-smart-commands";textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WrapAnywhere;text:host.smartPlanBusy?"Discovering physical devices…":host.smartPlan.error?host.smartPlan.error:host.smartPlan.commands.length?host.smartPlan.commands.join("\n"):"No confirmed device commands. No privileged read will start.";color:host.ink;font.family:Style.font.family;font.pixelSize:13}
            Flow {width:parent.width;spacing:8
                DoctorAction {objectName:"doctor-confirm-smart-verification";text:"Open verification terminal";primary:true;ink:host.ink;accent:host.good;enabled:!host.scanning&&!host.verifying&&!host.smartPlanBusy&&!host.smartPlan.error&&host.smartPlan.commands.length>0;onClicked:host.startSmartVerification()}
                DoctorAction {objectName:"doctor-cancel-smart-verification";text:"Cancel";ink:host.ink;onClicked:host.smartConfirmation=false}
            }
        }
    }
    Rectangle {visible:host.packageConfirmation;width:parent.width;height:approval.implicitHeight+32;radius:12;color:host.card;border.color:host.warning
        Column {id:approval;x:16;y:16;width:parent.width-32;spacing:10
            Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:"Run the read-only protected-file check?\nThe normal terminal will ask you to authenticate for sudo /usr/bin/pacman -Qk. Doctor itself stays unprivileged. No packages or permissions change.";color:host.ink;font.family:Style.font.family;font.pixelSize:14}
            Flow {width:parent.width;spacing:8
                DoctorAction {objectName:"doctor-confirm-package-verification";text:"Open verification terminal";primary:true;ink:host.ink;accent:host.good;onClicked:host.startPackageVerification()}
                DoctorAction {objectName:"doctor-cancel-package-verification";text:"Cancel";ink:host.ink;onClicked:host.packageConfirmation=false}
            }
        }
    }
    Text {textFormat:Text.PlainText;width:parent.width;wrapMode:Text.WordWrap;text:host.stale||!host.complete?"Other measurements are old or unfinished. After completing coverage, run Doctor once for fresh measurements. Real faults remain visible and prevent green.":"Other supported measurements are fresh. Any remaining access, decoding or collection failure stays gray with its evidence.";color:host.dim;font.family:Style.font.family;font.pixelSize:14}
    DoctorAction {objectName:"doctor-refresh-verification-checks";text:"Refresh other measurements";ink:host.ink;accent:host.good;enabled:!host.verifying&&!host.scanning;onClicked:host.refresh(false)}
}
