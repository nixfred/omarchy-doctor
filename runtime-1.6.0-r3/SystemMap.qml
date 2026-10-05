import QtQuick
import qs.Commons
import "Model.js" as Model

Item {
    id: root
    required property var host
    implicitHeight: 272
    property real phase: 0
    readonly property var nodes: [
        {key:"system",label:"SERVICES",x:0.13,y:0.23},
        {key:"ram",label:"MEMORY",x:0.13,y:0.74},
        {key:"disk",label:"STORAGE",x:0.87,y:0.23},
        {key:"gpu",label:"GRAPHICS",x:0.87,y:0.74},
        {key:"network",label:"NETWORK",x:0.50,y:0.06},
        {key:"devices",label:"DEVICES",x:0.50,y:0.94}
    ]
    Timer { interval:100; repeat:true; running:root.host.motion && root.host.opened && root.visible; onTriggered:{root.phase=(root.phase+0.024)%1;lines.requestPaint()} }
    Connections { target:root.host; function onResultsChanged(){lines.requestPaint()} }
    Canvas {
        id:lines; anchors.fill:parent
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            var c=getContext("2d"),w=width,h=height,cx=w/2,cy=h/2
            c.reset();c.clearRect(0,0,w,h)
            c.fillStyle=Qt.alpha(root.host.ink,0.07)
            for(var x=10;x<w;x+=20)for(var y=10;y<h;y+=20){c.beginPath();c.arc(x,y,0.7,0,Math.PI*2);c.fill()}
            root.nodes.forEach(function(n,i){
                var nx=n.x*w,ny=n.y*h,col=root.host.stateColor(Model.domainState(root.host.results,n.key))
                c.strokeStyle=Qt.alpha(col,0.25);c.lineWidth=1;c.beginPath();c.moveTo(cx,cy);c.lineTo((cx+nx)/2,ny);c.lineTo(nx,ny);c.stroke()
                var t=(root.phase+i/6)%1,px=cx+(nx-cx)*t,py=cy+(ny-cy)*Math.min(1,t*2)
                if(root.host.motion){c.fillStyle=Qt.alpha(col,0.8);c.beginPath();c.arc(px,py,1.8,0,Math.PI*2);c.fill()}
            })
        }
    }
    HardwareGlyph { anchors.centerIn:parent; width:170;height:170;kind:"core";tint:root.host.stateColor(root.host.overallState);surface:root.host.surface;animate:root.host.motion&&root.host.opened&&root.visible }
    Repeater {
        model:root.nodes
        Item {
            required property var modelData
            x:modelData.x*root.width-width/2;y:modelData.y*root.height-height/2
            width:100;height:44
            readonly property string status:Model.domainState(root.host.results,modelData.key)
            Rectangle { anchors.horizontalCenter:parent.horizontalCenter;y:17;width:7;height:7;radius:4;color:root.host.stateColor(parent.status) }
            Text {font.family:Style.font.family; anchors.horizontalCenter:parent.horizontalCenter;y:0;text:modelData.label;color:root.host.dim;font.pixelSize:10;font.letterSpacing:1.4 }
            Text {font.family:Style.font.family; anchors.horizontalCenter:parent.horizontalCenter;y:29;text:root.host.results.length ? Model.labels[parent.status] : "Waiting";color:root.host.ink;font.pixelSize:11 }
        }
    }
}
