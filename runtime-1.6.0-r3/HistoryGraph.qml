import QtQuick
import qs.Commons
import "Model.js" as Model

Item {
    id: root
    property var samples: []
    property string metric: "cpu_pct"
    property string unit: "%"
    property color tint: "#b6ef96"
    property color ink: "#eef5ed"
    property bool detailed: false
    property real ceiling: metric.indexOf("pct") >= 0 ? 100 : 0
    readonly property var points: Model.series(samples, metric)
    property int hoverIndex: -1
    implicitHeight: detailed ? 220 : 55
    onPointsChanged: drawing.requestPaint()
    onTintChanged: drawing.requestPaint()
    onInkChanged: drawing.requestPaint()
    onHoverIndexChanged: drawing.requestPaint()
    Canvas {
        id: drawing
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var c=getContext("2d"),w=width,h=height,pts=root.points,bottom=root.detailed?24:3,top=root.detailed?26:3
            c.reset();c.clearRect(0,0,w,h)
            c.strokeStyle=Qt.alpha(root.ink,0.08);c.lineWidth=1
            for(var g=0;g<4;g++){var yy=top+(h-top-bottom)*g/3;c.beginPath();c.moveTo(0,yy);c.lineTo(w,yy);c.stroke()}
            if(!pts.length)return
            var max=root.ceiling>0?root.ceiling:Math.max(1,Math.max.apply(null,pts.map(function(v){return v.value}))*1.15)
            var from=pts[0].time,to=pts[pts.length-1].time,span=Math.max(1,to-from)
            function x(i){return pts.length===1?w/2:4+(w-8)*(pts[i].time-from)/span}
            function y(i){return top+(h-top-bottom)*(1-Math.max(0,Math.min(1,pts[i].value/max)))}
            c.strokeStyle=root.tint;c.lineWidth=root.detailed?2:1.5;c.beginPath()
            for(var i=0;i<pts.length;i++) {
                // A closed-panel gap is missing data, not an interpolated line.
                if(i===0||pts[i].time-pts[i-1].time>120)c.moveTo(x(i),y(i));else c.lineTo(x(i),y(i))
            }
            c.stroke();c.fillStyle=root.tint
            for(var j=0;j<pts.length;j++){c.beginPath();c.arc(x(j),y(j),pts.length<8?2.8:1.3,0,Math.PI*2);c.fill()}
            if(root.hoverIndex>=0&&root.hoverIndex<pts.length){c.strokeStyle=Qt.alpha(root.ink,0.5);c.beginPath();c.moveTo(x(root.hoverIndex),top);c.lineTo(x(root.hoverIndex),h-bottom);c.stroke()}
            if(root.detailed){c.fillStyle=Qt.alpha(root.ink,0.60);c.font="10px monospace";c.fillText(max.toFixed(0)+" "+root.unit,3,13);c.fillText(new Date(from*1000).toLocaleTimeString(),3,h-3);c.textAlign="right";c.fillText(new Date(to*1000).toLocaleTimeString(),w-3,h-3)}
        }
    }
    Text {
        font.family:Style.font.family
        anchors.centerIn: parent
        visible: !root.points.length
        text: "History builds from real observations"
        color: Qt.alpha(root.ink,0.6)
        font.pixelSize: root.detailed ? 12 : 10
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onExited: root.hoverIndex=-1
        onPositionChanged: function(mouse) {
            if(!root.points.length)return
            var first=root.points[0].time,last=root.points[root.points.length-1].time
            var t=first+(last-first)*Math.max(0,Math.min(1,mouse.x/width)),best=0
            for(var i=1;i<root.points.length;i++)if(Math.abs(root.points[i].time-t)<Math.abs(root.points[best].time-t))best=i
            root.hoverIndex=best
        }
    }
    Rectangle {
        visible: root.hoverIndex>=0 && root.detailed
        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
        width: hoverLabel.implicitWidth+14; height: 23; radius: 5
        color: Qt.alpha(root.ink,0.1)
        Text {
            font.family:Style.font.family
            id: hoverLabel; anchors.centerIn: parent; color: root.ink; font.pixelSize:11
            text: root.hoverIndex>=0 && root.points[root.hoverIndex] ? root.points[root.hoverIndex].value.toFixed(1)+" "+root.unit+" · "+new Date(root.points[root.hoverIndex].time*1000).toLocaleTimeString() : ""
        }
    }
}
