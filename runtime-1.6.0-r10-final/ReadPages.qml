import QtQuick
import qs.Commons
// Explicit pages retain long evidence without wheel scrolling or shrinking text.
Item {
 id:root
 property color ink:Color.popups.text
 property color accent:Color.accent
 default property alias contentData:paper.data
 property int page:0
 readonly property real contentHeight:paper.childrenRect.height
 readonly property real viewportHeight:viewport.height
 readonly property real stride:Math.max(1,viewport.height-48)
 readonly property var offsets:makePages(contentHeight,viewport.height,width)
 readonly property int pageCount:offsets.length
 readonly property real contentY:offsets[Math.min(page,pageCount-1)]||0
 function makePages(total,space,availableWidth){
  if(space<96)return [0]
  var starts=[0],blocks=[]
  function visit(item,y){
   if(!item.visible)return
   var top=y+item.y
   if(item.text!==undefined&&item.height>0){blocks.push({top:top,bottom:top+item.height});return}
   for(var j=0;j<item.children.length;j++)visit(item.children[j],top)
  }
  for(var c=0;c<paper.children.length;c++)visit(paper.children[c],0)
  var offset=0
  while(offset+space<total){
   var next=offset+Math.max(1,space-48),candidate=next
   for(var i=0;i<blocks.length;i++){
    var b=blocks[i]
    if(b.top>offset+48&&b.top<candidate&&b.bottom>candidate&&b.bottom-b.top<=space-48)candidate=b.top
   }
   next=Math.max(offset+1,candidate)
   starts.push(next);offset=next
  }
  return starts
 }
 function reset(){page=0}
 onPageCountChanged:page=Math.min(page,pageCount-1)
 Item {id:viewport;width:parent.width;height:Math.max(1,parent.height-44);clip:true
  Item{id:paper;width:viewport.width;y:-root.contentY}
 }
 Row {anchors.bottom:parent.bottom;spacing:10
  DoctorAction{objectName:"doctor-page-previous";text:"Previous";enabled:root.page>0;ink:root.ink;accent:root.accent;onClicked:root.page--}
  Text{objectName:"doctor-page-counter";text:"Page "+(root.page+1)+" of "+root.pageCount;color:root.ink;font.family:Style.font.family;font.pixelSize:12;height:34;verticalAlignment:Text.AlignVCenter}
  DoctorAction{objectName:"doctor-page-next";text:"Next";enabled:root.page+1<root.pageCount;ink:root.ink;accent:root.accent;onClicked:root.page++}
 }
}
