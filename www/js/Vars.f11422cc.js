(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["Vars"],{"18dc":function(t,a,e){"use strict";var s=function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",[e("div",{staticClass:"panel"},[e("div",{staticClass:"panel-header"},[t._m(0),null!==t.$route.meta.error?e("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(a){t.$route.meta.error=null,t.$forceUpdate()}}}):t._e()],1),e("div",{staticClass:"panel-nav"},[e("div",{staticClass:"btn-group btn-group-block float-right"},[e("button",{staticClass:"btn",on:{click:function(a){return t.getPis()}}},[e("i",{staticClass:"icon icon-refresh centered"})]),e("button",{staticClass:"btn",on:{click:function(a){return t.openModal("Add new linked pi",-1,"","","","UDP",8888)}}},[e("i",{staticClass:"icon icon-plus centered"})])])]),e("div",{staticClass:"panel-body"},[e("div",{staticClass:"modal",class:{active:t.modalData.active}},[e("a",{staticClass:"modal-overlay",attrs:{"aria-label":"Close"},on:{click:function(a){t.modalData.active=!1}}}),e("div",{staticClass:"modal-container"},[e("div",{staticClass:"modal-header"},[e("a",{staticClass:"btn btn-clear float-right",attrs:{"aria-label":"Close"},on:{click:function(a){t.modalData.active=!1}}}),e("div",{staticClass:"modal-title h5"},[t._v(t._s(t.modalData.title))]),t.modalData.errors.length?e("Error",{attrs:{"error-array":t.modalData.errors},on:{"close-err":function(a){t.modalData.errors=[]}}}):t._e()],1),e("div",{staticClass:"modal-body"},[e("div",{staticClass:"content"},[e("form",{staticClass:"form-horizontal"},[e("div",{staticClass:"form-group"},[t._m(1),e("div",{staticClass:"col-9 col-sm-12"},[e("select",{directives:[{name:"model",rawName:"v-model",value:t.modalData.mode,expression:"modalData.mode"}],staticClass:"form-select",attrs:{id:"mode"},on:{change:function(a){var e=Array.prototype.filter.call(a.target.options,(function(t){return t.selected})).map((function(t){var a="_value"in t?t._value:t.value;return a}));t.$set(t.modalData,"mode",a.target.multiple?e:e[0])}}},[e("option",{attrs:{value:"UDP"}},[t._v("UDP")]),e("option",{attrs:{value:"HTTP"}},[t._v("HTTP")])])])]),e("div",{staticClass:"form-group"},[t._m(2),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.name,expression:"modalData.name"}],staticClass:"form-input",attrs:{type:"text",id:"name",placeholder:"Name"},domProps:{value:t.modalData.name},on:{input:function(a){a.target.composing||t.$set(t.modalData,"name",a.target.value)}}})])]),"HTTP"==t.modalData.mode?e("div",{staticClass:"form-group"},[t._m(3),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.url,expression:"modalData.url"}],staticClass:"form-input",attrs:{type:"text",id:"cmd",placeholder:"HTTP://HOST:PORT"},domProps:{value:t.modalData.url},on:{input:function(a){a.target.composing||t.$set(t.modalData,"url",a.target.value)}}})])]):e("div",{staticClass:"form-group"},[t._m(4),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.ip,expression:"modalData.ip"}],staticClass:"form-input",attrs:{type:"text",id:"ip"},domProps:{value:t.modalData.ip},on:{input:function(a){a.target.composing||t.$set(t.modalData,"ip",a.target.value)}}})])]),e("div",{directives:[{name:"show",rawName:"v-show",value:"UDP"==t.modalData.mode,expression:"modalData.mode == 'UDP'"}],staticClass:"form-group"},[t._m(5),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.port,expression:"modalData.port"}],staticClass:"form-input",attrs:{type:"number",id:"port"},domProps:{value:t.modalData.port},on:{input:function(a){a.target.composing||t.$set(t.modalData,"port",a.target.value)}}})])]),e("div",{staticClass:"form-group"},[t._m(6),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.password,expression:"modalData.password"}],staticClass:"form-input",attrs:{type:"password",id:"psw"},domProps:{value:t.modalData.password},on:{input:function(a){a.target.composing||t.$set(t.modalData,"password",a.target.value)}}})])])])])]),e("div",{staticClass:"modal-footer"},[e("button",{directives:[{name:"show",rawName:"v-show",value:-1!==t.modalData.id,expression:"modalData.id !== -1"}],staticClass:"btn btn-code float-left",attrs:{disabled:this.loading},on:{click:function(a){return t.modalAction(!0)}}},[e("i",{staticClass:"icon icon-delete"}),t._v(" Delete")]),e("button",{staticClass:"btn btn-primary",attrs:{disabled:this.loading},on:{click:function(a){return t.modalAction(!1)}}},[e("i",{staticClass:"icon icon-check"}),t._v(" Confirm")])])])]),e("div",{staticClass:"container"},[t.pis.length||t.loading?e("table",{staticClass:"table table-striped"},[t._m(8),e("tbody",t._l(t.pis,(function(a){return e("tr",{key:a.id},[e("td",[e("i",{staticClass:"icon icon-edit c-hand",on:{click:function(e){return t.openModal("Edit: "+a.name,a.id,a.name,a.url,a.password,a.mode,a.port)}}})]),e("td",[e("i",{staticClass:"icon",class:{"text-success icon-check":a.codeVersion,"text-error icon-cross":!a.codeVersion}})]),e("td",[t._v(t._s(a.name))]),e("td",[t._v(t._s(a.url))])])})),0)]):e("div",{staticClass:"empty centered"},[t._m(7),e("p",{staticClass:"empty-title h5"},[t._v("There are no linked pis configured")]),e("p",{staticClass:"empty-subtitle"},[t._v("Click the button to configure new")]),e("div",{staticClass:"empty-action"},[e("button",{staticClass:"btn btn-primary",on:{click:function(a){return t.openModal("Add new linked pi",-1,"","","","UDP",8888)}}},[e("i",{staticClass:"icon icon-plus centered"})])])])])]),e("div",{staticClass:"panel-footer"},[e("span",{staticClass:"text-secondary"},[t._v("Last update: "+t._s(t.updateDate))])])])])},o=[function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"panel-title"},[e("h3",[t._v("Linked pi devices")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"mode"}},[t._v("Connection mode")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"name"}},[t._v("Name")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"cmd"}},[t._v("Url")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"ip"}},[t._v("IP/HOST")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"port"}},[t._v("Port")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"psw"}},[t._v("Password")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"empty-icon"},[e("i",{staticClass:"icon icon-4x icon-cross"})])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("thead",[e("tr",[e("th",[t._v("Edit")]),e("th",[t._v("Active")]),e("th",[t._v("Name")]),e("th",[t._v("Url/Ip/Host")])])])}],l=e("3fb9"),i={name:"LinkedPis",data(){return{pis:[],updateDate:"",modalData:{active:!1,id:-1,title:"New linked pi device",name:"",url:"",mode:"UDP",port:8888,password:"",errors:[]}}},created(){this.getPis()},methods:{openModal(t,a,e,s,o,l,i){this.modalData.active=!0,this.modalData.title=t,this.modalData.name=e,this.modalData.url=s,this.modalData.ip=s,this.modalData.password=o,this.modalData.mode=l,this.modalData.port=i,this.modalData.id=a,this.modalData.errors=[]},modalAction(t){if(this.modalData.errors=[],t||(this.modalData.name||this.modalData.errors.push("Name required !"),this.modalData.url||"HTTP"!=this.modalData.mode||this.modalData.errors.push("Url required !"),this.modalData.ip&&this.modalData.port||"UDP"!=this.modalData.mode||this.modalData.errors.push("IP and Port required !")),!this.modalData.errors.length){let a="";a=t?"DeleteLinkedPi;"+this.modalData.id:-1===this.modalData.id?"AddLinkedPi;"+this.modalData.name+";"+("HTTP"==this.modalData.mode?this.modalData.url:this.modalData.ip)+";"+this.modalData.password+";"+this.modalData.mode+";"+this.modalData.port+";"+this.$moment.utc().format("YYYY-MM-DD HH:mm:ss.SSS"):"UpdateLinkedPi;"+this.modalData.id+";"+this.modalData.name+";"+("HTTP"==this.modalData.mode?this.modalData.url:this.modalData.ip)+";"+this.modalData.password+";"+this.modalData.mode+";"+this.modalData.port+";;"+this.$moment.utc().format("YYYY-MM-DD HH:mm:ss.SSS"),this.doPost(a).then(()=>{this.getPis(),this.modalData.active=!1}).catch(t=>{this.modalData.errors.push(t.message)})}},getPis(){this.doPost("GetLinkedPis;1").then(t=>{this.$route.meta.error=null,this.pis=[];for(var a=2;a<t.length-1;a+=7)this.pis.push({id:parseInt(t[a]),name:t[a+1],url:t[a+2],password:t[a+3],mode:t[a+4],port:parseInt(t[a+5]),codeVersion:parseInt(t[a+6])});this.updateDate=this.$moment().format("YYYY-MM-DD HH:mm:ss.SSS")}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})}},components:{Error:l["a"]}},r=i,n=e("2877"),c=Object(n["a"])(r,s,o,!1,null,null,null);a["a"]=c.exports},"3de4":function(t,a,e){"use strict";e.r(a);var s=function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"Variables"},[null!==t.$route.meta.error?e("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(a){t.$route.meta.error=null,t.$forceUpdate()}}}):e("div",{staticClass:"container"},[e("div",{staticClass:"columns"},[e("LinkedPis",{staticClass:"column col-6 col-lg-12"}),e("GlobalVariables",{staticClass:"column col-6 col-lg-12"})],1)])],1)},o=[],l=e("3fb9"),i=e("18dc"),r=function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",[e("div",{staticClass:"panel"},[e("div",{staticClass:"panel-header"},[t._m(0),null!==t.$route.meta.error?e("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(a){t.$route.meta.error=null,t.$forceUpdate()}}}):t._e()],1),e("div",{staticClass:"panel-nav"},[e("div",{staticClass:"btn-group btn-group-block float-right"},[e("button",{staticClass:"btn",on:{click:function(a){return t.getVars()}}},[e("i",{staticClass:"icon icon-refresh centered"})]),e("button",{staticClass:"btn",on:{click:function(a){return t.openModal("Add new var",-1,"","",!1)}}},[e("i",{staticClass:"icon icon-plus centered"})])])]),e("div",{staticClass:"panel-body"},[e("div",{staticClass:"modal",class:{active:t.modalData.active}},[e("a",{staticClass:"modal-overlay",attrs:{"aria-label":"Close"},on:{click:function(a){t.modalData.active=!1}}}),e("div",{staticClass:"modal-container"},[e("div",{staticClass:"modal-header"},[e("a",{staticClass:"btn btn-clear float-right",attrs:{"aria-label":"Close"},on:{click:function(a){t.modalData.active=!1}}}),e("div",{staticClass:"modal-title h5"},[t._v(t._s(t.modalData.title))]),t.modalData.errors.length?e("Error",{attrs:{"error-array":t.modalData.errors},on:{"close-err":function(a){t.modalData.errors=[]}}}):t._e()],1),e("div",{staticClass:"modal-body"},[e("div",{staticClass:"content"},[e("form",{staticClass:"form-horizontal"},[e("div",{staticClass:"form-group"},[t._m(1),e("div",{staticClass:"col-9 col-sm-12"},[e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.name,expression:"modalData.name"}],staticClass:"form-input",attrs:{type:"text",id:"name",placeholder:"Name"},domProps:{value:t.modalData.name},on:{input:function(a){a.target.composing||t.$set(t.modalData,"name",a.target.value)}}})])]),e("div",{staticClass:"form-group"},[t._m(2),e("div",{staticClass:"col-9 col-sm-12"},["String"==t.modalData.type?e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.val,expression:"modalData.val"}],staticClass:"form-input",attrs:{type:"text",id:"val",placeholder:"Default value"},domProps:{value:t.modalData.val},on:{input:function(a){a.target.composing||t.$set(t.modalData,"val",a.target.value)}}}):"Date"==t.modalData.type?e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.val,expression:"modalData.val"}],staticClass:"form-input",attrs:{type:"datetime-local",id:"val"},domProps:{value:t.modalData.val},on:{input:function(a){a.target.composing||t.$set(t.modalData,"val",a.target.value)}}}):"Time"==t.modalData.type?e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.val,expression:"modalData.val"}],staticClass:"form-input",attrs:{type:"time",id:"val"},domProps:{value:t.modalData.val},on:{input:function(a){a.target.composing||t.$set(t.modalData,"val",a.target.value)}}}):e("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.val,expression:"modalData.val"}],staticClass:"form-input",attrs:{type:"number",id:"val"},domProps:{value:t.modalData.val},on:{input:function(a){a.target.composing||t.$set(t.modalData,"val",a.target.value)}}})])]),e("div",{staticClass:"form-group"},[t._m(3),e("div",{staticClass:"col-9 col-sm-12"},[e("select",{directives:[{name:"model",rawName:"v-model",value:t.modalData.type,expression:"modalData.type"}],staticClass:"form-select",on:{change:function(a){var e=Array.prototype.filter.call(a.target.options,(function(t){return t.selected})).map((function(t){var a="_value"in t?t._value:t.value;return a}));t.$set(t.modalData,"type",a.target.multiple?e:e[0])}}},[e("option",{attrs:{value:"String"}},[t._v("String")]),e("option",{attrs:{value:"Date"}},[t._v("Date")]),e("option",{attrs:{value:"Time"}},[t._v("Time")]),e("option",{attrs:{value:"Number"}},[t._v("Number")])])])])])])]),e("div",{staticClass:"modal-footer"},[e("button",{directives:[{name:"show",rawName:"v-show",value:-1!==t.modalData.id,expression:"modalData.id !== -1"}],staticClass:"btn btn-code float-left",attrs:{disabled:this.loading},on:{click:function(a){return t.modalAction(!0)}}},[e("i",{staticClass:"icon icon-delete"}),t._v(" Delete")]),e("button",{staticClass:"btn btn-primary",attrs:{disabled:this.loading},on:{click:function(a){return t.modalAction(!1)}}},[e("i",{staticClass:"icon icon-check"}),t._v(" Confirm")])])])]),e("div",{staticClass:"container"},[t.vars.length||t.loading?e("table",{staticClass:"table table-striped"},[t._m(5),e("tbody",t._l(t.vars,(function(a){return e("tr",{key:a.id},[e("td",[e("i",{staticClass:"icon icon-edit c-hand",on:{click:function(e){return t.openModal("Edit: "+a.name,a.id,a.name,a.val,a.type)}}})]),e("td",[t._v(t._s(a.name))]),e("td",[t._v(t._s(a.val))]),e("td",[t._v(t._s(a.type))]),e("td",[t._v(t._s(a.timestamp))])])})),0)]):e("div",{staticClass:"empty centered"},[t._m(4),e("p",{staticClass:"empty-title h5"},[t._v("There are no variables configured")]),e("p",{staticClass:"empty-subtitle"},[t._v("Click the button to configure new")]),e("div",{staticClass:"empty-action"},[e("button",{staticClass:"btn btn-primary",on:{click:function(a){return t.openModal("Add new global variable",-1,"","",!1)}}},[e("i",{staticClass:"icon icon-plus centered"})])])])])]),e("div",{staticClass:"panel-footer"},[e("span",{staticClass:"text-secondary"},[t._v("Last update: "+t._s(t.updateDate))])])])])},n=[function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"panel-title"},[e("h3",[t._v("Global variables")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"name"}},[t._v("Name")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"val"}},[t._v("Value")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"col-3 col-sm-12"},[e("label",{staticClass:"form-label",attrs:{for:"val"}},[t._v("Type")])])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"empty-icon"},[e("i",{staticClass:"icon icon-4x icon-cross"})])},function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("thead",[e("tr",[e("th",[t._v("Edit")]),e("th",[t._v("Name")]),e("th",[t._v("Value")]),e("th",[t._v("Type")]),e("th",[t._v("Timestamp")])])])}],c={name:"GlobalVariables",data(){return{vars:[],updateDate:"",modalData:{active:!1,id:-1,title:"New global variable",name:"",val:"",type:"",errors:[]}}},props:{col:{type:String,default:"col-4 col-lg-6 col-sm-12"}},created(){this.getVars()},methods:{openModal(t,a,e,s,o){this.modalData.active=!0,this.modalData.title=t,this.modalData.name=e,this.modalData.val=s,this.modalData.type=o,this.modalData.id=a,this.modalData.errors=[]},modalAction(t){if(this.modalData.errors=[],t||(this.modalData.name||this.modalData.errors.push("Name required !"),this.modalData.type||this.modalData.errors.push("Type required !")),!this.modalData.errors.length){let a="";a=t?"DeleteGlobalVar;"+this.modalData.id:-1===this.modalData.id?"AddGlobalVar;"+this.modalData.name+";"+this.modalData.val+";"+this.modalData.type+";"+this.$moment.utc().format("YYYY-MM-DD HH:mm:ss.SSS"):"UpdateGlobalVar;"+this.modalData.id+";"+this.modalData.name+";"+this.modalData.val+";"+this.modalData.type+";"+this.$moment.utc().format("YYYY-MM-DD HH:mm:ss.SSS"),this.doPost(a).then(()=>{this.getVars(),this.modalData.active=!1}).catch(t=>{this.modalData.errors.push(t.message)})}},getVars(){this.doPost("GetGlobalVars").then(t=>{this.$route.meta.error=null,this.vars=[];for(var a=2;a<t.length-1;a+=5)this.vars.push({id:parseInt(t[a]),name:t[a+1],val:t[a+2],type:t[a+3],timestamp:this.$moment.utc(t[a+4],"YYYY-MM-DD HH:mm:ss").local().format("YYYY-MM-DD HH:mm:ss")});this.updateDate=this.$moment().format("YYYY-MM-DD HH:mm:ss.SSS")}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})}},components:{Error:l["a"]}},d=c,m=e("2877"),u=Object(m["a"])(d,r,n,!1,null,null,null),v=u.exports,p={name:"Vars",components:{Error:l["a"],LinkedPis:i["a"],GlobalVariables:v}},h=p,D=Object(m["a"])(h,s,o,!1,null,null,null);a["default"]=D.exports},"3fb9":function(t,a,e){"use strict";var s=function(){var t=this,a=t.$createElement,e=t._self._c||a;return e("div",{staticClass:"toast toast-error"},[e("button",{staticClass:"btn btn-clear float-right",on:{click:function(a){return t.$emit("close-err")}}}),""!==t.errorMessage&&null!==t.errorMessage?e("span",[t._v(" "+t._s(t.errorMessage)+" ")]):t._e(),t.errorArray.length&&null!==t.errorArray?e("ul",t._l(t.errorArray,(function(a,s){return e("li",{key:s},[t._v(t._s(a))])})),0):t._e()])},o=[],l={name:"Error",props:{errorMessage:{type:String,required:!1},errorArray:{default:()=>[],type:Array,required:!1}}},i=l,r=e("2877"),n=Object(r["a"])(i,s,o,!1,null,null,null);a["a"]=n.exports}}]);