(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["Rf"],{3890:function(t,e,a){"use strict";a.r(e);var s=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"RF"},[null!==t.$route.meta.error?a("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(e){t.$route.meta.error=null,t.$forceUpdate()}}}):a("div",{staticClass:"container"},[a("div",{staticClass:"columns"},[a("RfCodes",{staticClass:"column col-6 col-md-12"}),a("RfHistory",{staticClass:"column col-6 col-md-12"})],1)])],1)},o=[],i=a("3fb9"),r=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",[a("div",{staticClass:"panel"},[a("div",{staticClass:"panel-header"},[t._m(0),null!==t.$route.meta.error?a("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(e){t.$route.meta.error=null,t.$forceUpdate()}}}):t._e()],1),a("div",{staticClass:"panel-nav"},[a("div",{staticClass:"btn-group btn-group-block float-right"},[a("button",{staticClass:"btn",on:{click:function(e){return t.getRfCodes()}}},[a("i",{staticClass:"icon icon-refresh centered"})]),a("button",{staticClass:"btn",on:{click:function(e){t.openModal(-1,"Add new RF code: ","",t.rx?"Recive":"Transmit","",350,1,(t.tx,10),24)}}},[a("i",{staticClass:"icon icon-plus centered"})])])]),a("div",{staticClass:"panel-body"},[a("div",{staticClass:"modal",class:{active:t.modalData.active}},[a("a",{staticClass:"modal-overlay",attrs:{"aria-label":"Close"},on:{click:function(e){t.modalData.active=!1}}}),a("div",{staticClass:"modal-container"},[a("div",{staticClass:"modal-header"},[a("a",{staticClass:"btn btn-clear float-right",attrs:{"aria-label":"Close"},on:{click:function(e){t.modalData.active=!1}}}),a("div",{staticClass:"modal-title h5"},[t._v(t._s(t.modalData.title))]),t.modalData.errors.length?a("Error",{attrs:{"error-array":t.modalData.errors},on:{"close-err":function(e){t.modalData.errors=[]}}}):t._e()],1),a("div",{staticClass:"modal-body"},[a("div",{staticClass:"content"},[a("form",{staticClass:"form-horizontal"},[a("div",{staticClass:"form-group"},[t._m(1),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.name,expression:"modalData.name"}],staticClass:"form-input",attrs:{type:"text",id:"name",placeholder:"Name"},domProps:{value:t.modalData.name},on:{input:function(e){e.target.composing||t.$set(t.modalData,"name",e.target.value)}}})])]),a("div",{staticClass:"form-group"},[t._m(2),a("div",{staticClass:"col-9 col-sm-12"},[a("select",{directives:[{name:"model",rawName:"v-model",value:t.modalData.type,expression:"modalData.type"}],staticClass:"form-select",on:{change:function(e){var a=Array.prototype.filter.call(e.target.options,(function(t){return t.selected})).map((function(t){var e="_value"in t?t._value:t.value;return e}));t.$set(t.modalData,"type",e.target.multiple?a:a[0])}}},[a("option",{attrs:{value:"Transmit",disabled:!t.tx}},[t._v("Transmit")]),a("option",{attrs:{value:"Recive",disabled:!t.rx}},[t._v("Recive")])])])]),a("div",{staticClass:"form-group"},[t._m(3),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.code,expression:"modalData.code"}],staticClass:"form-input",attrs:{type:"number",id:"code",placeholder:"RF Code"},domProps:{value:t.modalData.code},on:{input:function(e){e.target.composing||t.$set(t.modalData,"code",e.target.value)}}})])]),a("div",{staticClass:"form-group"},[t._m(4),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.pulseLength,expression:"modalData.pulseLength"}],staticClass:"form-input",attrs:{min:"0",type:"number",id:"Pulse",placeholder:"Pulse length"},domProps:{value:t.modalData.pulseLength},on:{input:function(e){e.target.composing||t.$set(t.modalData,"pulseLength",e.target.value)}}})])]),a("div",{staticClass:"form-group"},[t._m(5),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.protocol,expression:"modalData.protocol"}],staticClass:"form-input",attrs:{min:"1",max:"5",type:"number",id:"Protocol",placeholder:"Protocol"},domProps:{value:t.modalData.protocol},on:{change:function(e){return t.changePulseforProtocol()},input:function(e){e.target.composing||t.$set(t.modalData,"protocol",e.target.value)}}})])]),"Transmit"==t.modalData.type?a("div",{staticClass:"form-group"},[t._m(6),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.repeatTransmit,expression:"modalData.repeatTransmit"}],staticClass:"form-input",attrs:{min:"0",type:"number",id:"repeatTransmit",placeholder:"Repeat transmit"},domProps:{value:t.modalData.repeatTransmit},on:{input:function(e){e.target.composing||t.$set(t.modalData,"repeatTransmit",e.target.value)}}})])]):t._e(),a("div",{staticClass:"form-group"},[t._m(7),a("div",{staticClass:"col-9 col-sm-12"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.modalData.bitLength,expression:"modalData.bitLength"}],staticClass:"form-input",attrs:{min:"0",type:"number",id:"bitLength",placeholder:"Bit length"},domProps:{value:t.modalData.bitLength},on:{input:function(e){e.target.composing||t.$set(t.modalData,"bitLength",e.target.value)}}})])])])])]),a("div",{staticClass:"modal-footer"},[a("button",{directives:[{name:"show",rawName:"v-show",value:-1!==t.modalData.id,expression:"modalData.id !== -1"}],staticClass:"btn btn-code float-left",attrs:{disabled:this.loading},on:{click:function(e){return t.modalAction(!0)}}},[a("i",{staticClass:"icon icon-delete"}),t._v(" Delete")]),a("button",{staticClass:"btn btn-primary",attrs:{disabled:this.loading},on:{click:function(e){return t.modalAction(!1)}}},[a("i",{staticClass:"icon icon-check"}),t._v(" Confirm")])])])]),a("div",{staticClass:"container"},[t.codes.length||t.loading?a("div",{staticClass:"columns"},t._l(t.codes,(function(e,s){return a("div",{key:e.id,staticClass:"column",class:[t.col]},[a("div",{staticClass:"tile tile-centered"},[a("div",{staticClass:"tile-icon"},["Recive"==e.type?a("button",{staticClass:"btn btn-action btn-lg unclickable"},[a("i",{staticClass:"icon icon-download centered"})]):"Transmit"==e.type?a("button",{staticClass:"btn btn-action btn-lg",class:{"btn-success unclickable":e.transmiting},on:{click:function(a){return t.sendRfCode(e.id,s)}}},[a("i",{staticClass:"icon icon-upload centered"})]):t._e()]),a("div",{staticClass:"tile-content"},[a("div",{staticClass:"tile-title"},[t._v(t._s(e.name))]),a("div",{staticClass:"tile-subtitle text-gray"},[t._v(t._s(e.code))])]),a("div",{staticClass:"tile-action"},[a("button",{staticClass:"btn btn-link",on:{click:function(a){return t.openModal(e.id,"Edit: "+e.name,e.name,e.type,e.code,e.pulseLength,e.protocol,e.repeatTransmit,e.bitLength)}}},[a("i",{staticClass:"icon icon-edit"})])])])])})),0):a("div",{staticClass:"empty centered"},[t._m(8),a("p",{staticClass:"empty-title h5"},[t._v("There are no rf codes configured")]),a("p",{staticClass:"empty-subtitle"},[t._v("Click the button to configure new")]),a("div",{staticClass:"empty-action"},[a("button",{staticClass:"btn btn-primary",on:{click:function(e){t.openModal(-1,"Add new RF code: ","",t.rx?"Recive":"Transmit","",350,1,t.tx?10:"",24)}}},[a("i",{staticClass:"icon icon-plus centered"})])])])])]),a("div",{staticClass:"panel-footer"},[a("span",{staticClass:"text-secondary"},[t._v("Last update: "+t._s(t.updateDate))]),a("div",{staticClass:"float-right tooltip tooltip-left",attrs:{"data-tooltip":"Auto refresh time (s)"}},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.autoRefreshTime,expression:"autoRefreshTime"}],staticClass:"form-input input-sm",attrs:{type:"number",id:"autorefresh"},domProps:{value:t.autoRefreshTime},on:{change:function(e){return t.autoRefresh()},input:function(e){e.target.composing||(t.autoRefreshTime=e.target.value)}}})])])])])},l=[function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"panel-title"},[a("h3",[t._v("Radio frequency Transmit/Recive Codes")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"name"}},[t._v("Name")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"gpio"}},[t._v("Type")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"code"}},[t._v("Code")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"Pulse"}},[t._v("Pulse length")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"Protocol"}},[t._v("Protocol")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"repeatTransmit"}},[t._v("Repeat transmit")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"col-3 col-sm-12"},[a("label",{staticClass:"form-label",attrs:{for:"bitLength"}},[t._v("Bit length")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"empty-icon"},[a("i",{staticClass:"icon icon-4x icon-cross"})])}],n={name:"RfCodes",data(){return{codes:[],rx:0,tx:0,refreshInterval:"",updateDate:"",autoRefreshTime:5,modalData:{active:!1,id:-1,title:"New RF code",name:"",type:"Transmit",code:"",pulseLength:350,protocol:1,repeatTransmit:10,bitLength:24,errors:[]}}},props:{col:{type:String,default:"col-4 col-lg-6 col-sm-12"}},created(){this.doPost("GetRfPins").then(t=>{this.$route.meta.error=null,this.rx=parseInt(t[2]),this.tx=parseInt(t[3]),this.rx||this.tx?(this.getRfCodes(),this.autoRefresh()):(this.$route.meta.error="RF hardware not configured !",this.$forceUpdate())}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()}),this.$cookies.isKey("rf_arTime")&&(this.autoRefreshTime=parseInt(this.$cookies.get("rf_arTime")))},beforeDestroy(){clearTimeout(this.refreshInterval)},methods:{autoRefresh(){this.$cookies.set("rf_arTime",this.autoRefreshTime,-1),clearTimeout(this.refreshInterval),this.autoRefreshTime>0&&(this.refreshInterval=setTimeout(()=>{this.modalData.active||this.getRfCodes(),this.autoRefresh()},1e3*this.autoRefreshTime))},openModal(t,e,a,s,o,i,r,l,n){this.modalData.active=!0,this.modalData.id=t,this.modalData.title=e,this.modalData.name=a,this.modalData.type=s,this.modalData.code=o,this.modalData.pulseLength=i,this.modalData.protocol=r,this.modalData.repeatTransmit=l,this.modalData.bitLength=n,this.modalData.errors=[]},modalAction(t){if(this.modalData.errors=[],t||this.modalData.name&&this.modalData.code||this.modalData.errors.push("Name and code are required !"),!this.modalData.errors.length){let e="";e=t?["DeleteRfCode",this.modalData.id].join(";"):-1===this.modalData.id?["AddRfCode",this.modalData.name,this.modalData.type,this.modalData.code,this.modalData.pulseLength,this.modalData.protocol,this.modalData.repeatTransmit,this.modalData.bitLength].join(";"):["UpdateRfCode",this.modalData.id,this.modalData.name,this.modalData.type,this.modalData.code,this.modalData.pulseLength,this.modalData.protocol,this.modalData.repeatTransmit,this.modalData.bitLength].join(";"),this.doPost(e).then(()=>{this.getRfCodes(),this.modalData.active=!1}).catch(t=>{this.modalData.errors.push(t.message)})}},getRfCodes(){this.doPost("GetRfCodes").then(t=>{this.$route.meta.error=null,this.codes=[];for(var e=2;e<t.length-1;e+=8)this.codes.push({id:parseInt(t[e]),name:t[e+1],type:t[e+2],code:t[e+3],pulseLength:t[e+4],protocol:t[e+5],repeatTransmit:t[e+6],bitLength:t[e+7],transmiting:!1});this.updateDate=this.$moment().format("YYYY-MM-DD HH:mm:ss.SSS")}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})},sendRfCode(t,e){this.codes[e].transmiting=!0,this.doPost("SendRfCode;"+t).then(()=>{this.$route.meta.error=null,this.updateDate=this.$moment().format("YYYY-MM-DD HH:mm:ss.SSS")}).finally(()=>{this.codes[e].transmiting=!1}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})},changePulseforProtocol(){switch(this.modalData.protocol){case"1":this.modalData.pulseLength=350;break;case"2":this.modalData.pulseLength=650;break;case"3":this.modalData.pulseLength=100;break;case"4":this.modalData.pulseLength=380;break;case"5":this.modalData.pulseLength=500;break}}},components:{Error:i["a"]}},c=n,m=a("2877"),d=Object(m["a"])(c,r,l,!1,null,null,null),u=d.exports,h=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",[a("div",{staticClass:"panel"},[a("div",{staticClass:"panel-header"},[t._m(0),null!==t.$route.meta.error?a("Error",{attrs:{"error-message":t.$route.meta.error},on:{"close-err":function(e){t.$route.meta.error=null,t.$forceUpdate()}}}):t._e()],1),a("div",{staticClass:"panel-nav"},[a("div",{staticClass:"input-group filter"},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.dateFrom,expression:"dateFrom"}],staticClass:"form-input input-sm",attrs:{type:"date",placeholder:"Date from"},domProps:{value:t.dateFrom},on:{input:function(e){e.target.composing||(t.dateFrom=e.target.value)}}}),a("input",{directives:[{name:"model",rawName:"v-model",value:t.dateTo,expression:"dateTo"}],staticClass:"form-input input-sm",attrs:{type:"date",placeholder:"Date to"},domProps:{value:t.dateTo},on:{input:function(e){e.target.composing||(t.dateTo=e.target.value)}}}),a("button",{staticClass:"btn input-group-btn btn-sm",on:{click:function(e){return t.getHistory()}}},[a("i",{staticClass:"icon icon-refresh centered"})]),a("button",{staticClass:"btn btn-sm",on:{click:function(e){t.sniffModalActive=!0}}},[t._v("Sniffer")])])]),a("div",{staticClass:"panel-body"},[a("div",{staticClass:"modal",class:{active:t.sniffModalActive}},[a("a",{staticClass:"modal-overlay",attrs:{"aria-label":"Close"},on:{click:function(e){t.sniffModalActive=!1}}}),a("div",{staticClass:"modal-container log-container"},[a("div",{staticClass:"modal-header"},[t._m(1),a("a",{staticClass:"btn btn-clear float-right",attrs:{"aria-label":"Close"},on:{click:function(e){t.sniffModalActive=!1}}})]),a("div",{staticClass:"modal-body"},[t.sniffModalActive?a("RfSniffer"):t._e()],1)])]),t.history.length?a("table",{staticClass:"table table-striped"},[t._m(2),a("tbody",t._l(t.history,(function(e,s){return a("tr",{key:s},[a("td",[t._v(t._s(e.name))]),a("td",[t._v(t._s(e.type))]),a("td",[t._v(t._s(e.code))]),a("td",[t._v(t._s(e.date))]),a("td",[t._v(t._s(e.pulseLength))]),a("td",[t._v(t._s(e.protocol))]),a("td",[t._v(t._s(e.bitLength))])])})),0)]):a("div",{staticClass:"empty centered"},[t._m(3),a("p",{staticClass:"empty-title h5"},[t._v("There are is no data in the selected range")])])]),a("div",{staticClass:"panel-footer"},[a("span",{staticClass:"text-secondary"},[t._v("Last update: "+t._s(t.updateDate))]),a("div",{staticClass:"float-right tooltip tooltip-left",attrs:{"data-tooltip":"Auto refresh time (s)"}},[a("input",{directives:[{name:"model",rawName:"v-model",value:t.autoRefreshTime,expression:"autoRefreshTime"}],staticClass:"form-input input-sm",attrs:{type:"number",id:"autorefresh"},domProps:{value:t.autoRefreshTime},on:{change:function(e){return t.autoRefresh()},input:function(e){e.target.composing||(t.autoRefreshTime=e.target.value)}}})])])])])},f=[function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"panel-title"},[a("h3",[t._v("History")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"modal-title h5"},[t._v("RF Sniffer"),a("div",{staticClass:"loading float-right"})])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("thead",[a("tr",[a("th",[t._v("Name")]),a("th",[t._v("Type")]),a("th",[t._v("Code")]),a("th",[t._v("Date")]),a("th",[t._v("Pulse length")]),a("th",[t._v("Protocol")]),a("th",[t._v("Bit length")])])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"empty-icon"},[a("i",{staticClass:"icon icon-4x icon-cross"})])}],p=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",[t.logs.length?a("table",{staticClass:"table table-striped logs"},[t._m(0),a("tbody",t._l(t.logs,(function(e,s){return a("tr",{key:s},[a("td",[t._v(t._s(e.time))]),a("td",[t._v(t._s(e.code))]),a("td",[t._v(t._s(e.pulseLength))]),a("td",[t._v(t._s(e.protocol))]),a("td",[t._v(t._s(e.bitLength))])])})),0)]):a("div",{staticClass:"empty centered"},[t._m(1),a("p",{staticClass:"empty-title h5"},[t._v("Nothing here...")])])])},v=[function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("thead",[a("tr",[a("th",[t._v("Time")]),a("th",[t._v("Code")]),a("th",[t._v("Pulse length")]),a("th",[t._v("Protocol")]),a("th",[t._v("Bit length")])])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"empty-icon"},[a("i",{staticClass:"icon icon-4x icon-cross"})])}],g={name:"RfSniffer",data(){return{logs:[],refreshInterval:"",loading:!1}},created(){this.getData(),this.refreshInterval=setInterval(()=>{this.loading||this.getData()},1e3)},beforeDestroy(){clearInterval(this.refreshInterval)},methods:{getData(){this.loading=!0,this.doQPost("SniffRfCodes").then(t=>{this.logs=[];for(let e=2;e<t.length;e+=5)this.logs.push({code:t[e],pulseLength:t[e+1],protocol:t[e+2],bitLength:t[e+3],time:this.$moment.utc(t[e+4],"YYYY-MM-DD HH:mm:ss.SSS").local().format("HH:mm:ss")})}).finally(()=>{this.loading=!1}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})}}},C=g,_=Object(m["a"])(C,p,v,!1,null,null,null),b=_.exports,D={name:"RFHistory",data(){return{history:[],sniffModalActive:!1,refreshInterval:"",updateDate:"",autoRefreshTime:5,dateFrom:"",dateTo:""}},created(){this.dateFrom=this.$moment().subtract(7,"days").format("YYYY-MM-DD"),this.dateTo=this.$moment().add(1,"days").format("YYYY-MM-DD"),this.getHistory(),this.$cookies.isKey("hrf_arTime")&&(this.autoRefreshTime=parseInt(this.$cookies.get("hrf_arTime"))),this.autoRefresh()},beforeDestroy(){clearTimeout(this.refreshInterval)},methods:{autoRefresh(){this.$cookies.set("hrf_arTime",this.autoRefreshTime,-1),clearTimeout(this.refreshInterval),this.autoRefreshTime>0&&(this.refreshInterval=setTimeout(()=>{this.getHistory(),this.autoRefresh()},1e3*this.autoRefreshTime))},getHistory(){this.dateFrom&&this.dateTo&&this.doPost("GetRfHistory;"+this.$moment(this.dateFrom,"YYYY-MM-DD").utc().format("YYYY-MM-DD")+";"+this.$moment(this.dateTo+" 23:59:59","YYYY-MM-DD HH:mm:ss").utc().format("YYYY-MM-DD")+";"+this.category).then(t=>{this.$route.meta.error=null,this.history=[];for(var e=2;e<t.length-1;e+=7)this.history.push({name:t[e],type:t[e+1],code:t[e+2],date:this.$moment.utc(t[e+3],"YYYY-MM-DD HH:mm:ss.SSS").local().format("YYYY-MM-DD HH:mm:ss"),pulseLength:t[e+4],protocol:t[e+5],bitLength:t[e+6]});this.updateDate=this.$moment().format("YYYY-MM-DD HH:mm:ss.SSS")}).catch(t=>{this.$route.meta.error=t.message,this.$forceUpdate()})}},components:{Error:i["a"],RfSniffer:b}},y=D,$=Object(m["a"])(y,h,f,!1,null,null,null),R=$.exports,T={name:"Rfs",components:{Error:i["a"],RfCodes:u,RfHistory:R}},Y=T,M=Object(m["a"])(Y,s,o,!1,null,null,null);e["default"]=M.exports},"3fb9":function(t,e,a){"use strict";var s=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"toast toast-error"},[a("button",{staticClass:"btn btn-clear float-right",on:{click:function(e){return t.$emit("close-err")}}}),""!==t.errorMessage&&null!==t.errorMessage?a("span",[t._v(" "+t._s(t.errorMessage)+" ")]):t._e(),t.errorArray.length&&null!==t.errorArray?a("ul",t._l(t.errorArray,(function(e,s){return a("li",{key:s},[t._v(t._s(e))])})),0):t._e()])},o=[],i={name:"Error",props:{errorMessage:{type:String,required:!1},errorArray:{default:()=>[],type:Array,required:!1}}},r=i,l=a("2877"),n=Object(l["a"])(r,s,o,!1,null,null,null);e["a"]=n.exports}}]);