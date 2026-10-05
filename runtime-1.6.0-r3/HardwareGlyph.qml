import QtQuick

Item {
    id: root
    objectName: "doctor-hardware"
    property string kind: "core"
    property color tint: "#b6ef96"
    property color surface: "#11191c"
    property bool animate: false
    property real level: 0
    property real phase: 0
    implicitWidth: 100
    implicitHeight: 100
    Timer {
        interval: 100; repeat: true; running: root.animate && root.visible
        onTriggered: { root.phase = (root.phase + 0.016) % 1; drawing.requestPaint() }
    }
    onTintChanged: drawing.requestPaint()
    onSurfaceChanged: drawing.requestPaint()
    onLevelChanged: drawing.requestPaint()
    onKindChanged: drawing.requestPaint()
    onVisibleChanged: if (visible) drawing.requestPaint()
    Canvas {
        id: drawing
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var c=getContext("2d"),w=width,h=height,s=Math.min(w,h),p=root.phase*Math.PI*2
            c.reset(); c.clearRect(0,0,w,h); c.translate(w/2,h/2); c.scale(s/100,s/100)
            c.strokeStyle=root.tint; c.lineWidth=1.4; c.lineJoin="round"
            var compact=s<45
            if(!compact) {
                var g=c.createRadialGradient(0,0,8,0,0,49)
                g.addColorStop(0,Qt.alpha(root.tint,0.12));g.addColorStop(1,"transparent")
                c.fillStyle=g;c.fillRect(-50,-50,100,100)
            }
            function line(points) {c.beginPath();points.forEach(function(v,i){if(i)c.lineTo(v[0],v[1]);else c.moveTo(v[0],v[1])});c.stroke()}
            function circle(x,y,r){c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.stroke()}
            if(root.kind==="core") {
                if(!compact) for(var ring=0;ring<3;ring++) {
                    c.strokeStyle=Qt.alpha(root.tint,0.13);circle(0,0,32+ring*7)
                    c.strokeStyle=Qt.alpha(root.tint,0.65);c.beginPath();var a=p*(ring%2?-1:1)+ring*2;c.arc(0,0,32+ring*7,a,a+0.6);c.stroke()
                }
                c.strokeStyle=root.tint;c.fillStyle=root.surface;c.fillRect(-24,-24,48,48);c.strokeRect(-24,-24,48,48)
                c.strokeStyle=Qt.alpha(root.tint,0.18+0.10*Math.sin(p));c.lineWidth=4;c.strokeRect(-28,-28,56,56)
                c.strokeStyle=root.tint;c.lineWidth=2
                line([[-19,0],[-12,0],[-7,-8],[0,12],[8,-14],[13,0],[20,0]])
            } else if(root.kind==="cpu") {
                c.fillStyle=root.surface;c.fillRect(-24,-24,48,48);c.strokeRect(-24,-24,48,48)
                for(var pin=0;pin<4;pin++){var pos=-18+pin*12;line([[pos,-32],[pos,-24]]);line([[pos,24],[pos,32]]);line([[-32,pos],[-24,pos]]);line([[24,pos],[32,pos]])}
                for(var cell=0;cell<16;cell++) {
                    var energy=0.15+0.65*Math.max(0,Math.min(1,root.level/100))*(0.65+0.35*Math.sin(p+cell))
                    c.fillStyle=Qt.alpha(root.tint,energy);c.fillRect(-19+(cell%4)*10,-19+Math.floor(cell/4)*10,8,8)
                }
                c.strokeStyle=Qt.alpha(root.tint,0.7);var sweep=-22+root.phase*44;line([[sweep,-22],[sweep,22]])
            } else if(root.kind==="ram") {
                c.strokeRect(-36,-18,72,36)
                c.save();c.beginPath();c.rect(-35,-17,70,34);c.clip()
                var fillY=17-34*Math.max(0,Math.min(1,root.level/100)),wave=Math.sin(p)*3
                c.fillStyle=Qt.alpha(root.tint,0.2);c.beginPath();c.moveTo(-35,fillY);c.bezierCurveTo(-15,fillY+wave,15,fillY-wave,35,fillY);c.lineTo(35,17);c.lineTo(-35,17);c.closePath();c.fill();c.restore()
                for(var chip=0;chip<4;chip++){c.fillStyle=Qt.alpha(root.tint,0.14+root.level/160);c.fillRect(-29+chip*16,-11,11,22);c.strokeRect(-29+chip*16,-11,11,22)}
                for(var contact=0;contact<9;contact++)line([[-29+contact*7,18],[-29+contact*7,26]])
            } else if(root.kind==="disk") {
                c.strokeRect(-28,-36,56,72);circle(0,-3,21);circle(0,-3,5)
                c.save();c.translate(0,-3);c.rotate(p);c.strokeStyle=Qt.alpha(root.tint,0.35);line([[6,0],[19,0]]);c.restore()
                line([[20,22],[0,-3]]);line([[-20,28],[-10,28]])
            } else if(root.kind==="gpu") {
                c.strokeRect(-37,-22,70,44);circle(-10,0,16);circle(-10,0,4)
                c.save();c.translate(-10,0);c.rotate(p);for(var blade=0;blade<4;blade++){c.rotate(Math.PI/2);line([[5,0],[14,4],[10,9]])}c.restore()
                for(var fin=0;fin<4;fin++)line([[13,-13+fin*8],[25,-13+fin*8]])
                line([[-28,22],[-28,30],[7,30],[7,22]]);line([[38,-29],[38,27]])
            }
        }
    }
}
