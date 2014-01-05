String.prototype.toHHMMSS = function () {
    var sec_num = parseInt(this, 10); // don't forget the second parm
    var hours   = Math.floor(sec_num / 3600);
    var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
    var seconds = sec_num - (hours * 3600) - (minutes * 60);
	var has_hours = ( hours > 0);
    if (hours   < 10) {hours   = "0"+hours;}
    if (minutes < 10) {minutes = "0"+minutes;}
    if (seconds < 10) {seconds = "0"+seconds;}
    var time = ""
    
    if(has_hours) {
	    time += hours+':'
    }
    time    += minutes+':'+seconds;
    return time;
}


jQuery.fn.insertAt = function(index, element) {
  var lastIndex = this.children().size()
  if (index < 0) {
    index = Math.max(0, lastIndex + 1 + index)
  }
  this.append(element)
  if (index < lastIndex) {
    this.children().eq(index).before(this.children().last())
  }
  return this;
}


var PimmerUrls = {
	sync: "sync",
	play: "action/play",
	pause: "action/pause",
	stop: "action/stop",
	next: "action/next",
	prev: "action/prev",
	poll: "status",
	library: "library",
	deleteid: "action/deleteid",
	add: "action/add",
	moveid: "action/moveid",
	playid: "action/playid",
	load: "action/load",
	clearload: "action/clearload",
	save: "action/save",
	rm: "action/rm",
	random: "action/random"
}

var PimmerData = {
	init: function(){
		var t = this;
		t.poll();
		
		t.pollInterval = setInterval(function(){
			t.poll();
		},1000);
	},
	data : {
		"currentsong" : {},
		"status" : {},
		"playlist" : {},
		"playlists" : {}
	},
	callbacks: {},
	add_callback: function(item, callback){
		var t = this;
		if(typeof t.callbacks[item] == "undefined"){
			t.callbacks[item] = [];
		}
		t.callbacks[item].push(callback);	
	},
	update : function(data, callback){
		var t = this;
		
		$.each(data, function(i,v){
			var _fire = false;
			var _old = false;
			if(typeof t.data[i] != "undefined"){
				_old = t.data[i];
			}
			t.data[i] = v;
			_fire = _old !== v;
			
			if(typeof t.callbacks[i] != "undefined" && _fire){
				
				
				for(var j=0; j < t.callbacks[i].length; j++){
					_c = t.callbacks[i][j];
					_c.apply(t);
				}
			}
		});
		
		if (typeof callback == "function")
			callback(PimmerData);
	},
	send : function(action, data, callback){
			var t = this;
			var send_url = PimmerUrls[action];
			if(typeof data == "undefined")
				data = {}
			$.ajax({
				url: send_url,
				type: 'GET',
				data: data,
	  			dataType: "json",
	  			success: function(data){
		  			
		  			PimmerData.update(data, callback);
	  			}
	  		});
			
   	},
	poll : function(callback){
		var t = this;
		var poll_url = PimmerUrls["poll"];
		
		if(t.xHr && t.xHr.readyState != 4) {
			t.xHr.abort();
			console.log("aborted");
		}
		
		t.xHr = $.ajax({
					url: poll_url,
					type: 'GET',
					dataType: "json",
					success: function(data){
		  				
		  				t.update(data, callback);
		  			}
		  		});

		
	}
}

var PimmerPlayer = {
	
	init: function() {
		var t = this;
		
		t.tick = false;
		
		t.elapsed = 0;
		t.currentsong_length = 0;
		t.state = false;
		
		t.xHr = false;
		
		t.$elapsed = $("#player-elapsed");
		t.$progressBar = t.$elapsed.find(".progress-bar");
		
		t.$randomBtn = $("#random");
		t.is_random = false;
		
		var last_state = false;
		
		PimmerData.add_callback("status", function(){
			_state = this.data.status.state
			t.elapsed = this.data.elapsed;
			t.currentsong_length = parseInt(this.data.currentsong["time"]);
			
			var is_random = parseInt(this.data.status["random"]);
			
			if(t.is_random != is_random){
				t.$randomBtn.toggleClass("active", is_random == 1);
				
				if(is_random == 1){
					
					t.$randomBtn.data("random",0);
				} else {
					t.$randomBtn.data("random",1);
				}
				
			}
			
			t.is_random = is_random;
			
			
			
			if(isNaN(t.currentsong_length)){
				t.currentsong_length = 0;
			}
			
			if(t.state == _state)
				return;
			
			switch(_state){
				case "play":
					$("#play").addClass("disabled");
					$("#stop").removeClass("disabled");
					$("#pause").removeClass("disabled");
					
					t.tick = true;
					
					break;
				case "pause":
				    $("#play").removeClass("disabled");
				    $("#pause").addClass("disabled");
				    $("#stop").addClass("disabled");
				    
				    t.tick = false;
				    break;
				case "stop":
					
				    $("#play").removeClass("disabled");
				    $("#pause").addClass("disabled");
				    $("#stop").addClass("disabled");
				    
				    t.elapsed = 0;
				    t.tick = false;
				    break;
			}
			
			t.state = _state;
			
		})
		
		$(document).on("click","#play",function(){
			t.actions.play();
			t.state = "play";
			t.tick = true;
			t.updatePlayer();
		});
		$(document).on("click","#pause",function(){
			t.actions.pause();
			t.state = "pause";
			t.tick = false;
			t.updatePlayer();
		});
		$(document).on("click","#stop",function(){
			t.actions.stop();
			t.state = "stop";
			t.tick = false;
			t.updatePlayer();
		});
		$(document).on("click","#next",function(){t.actions.next();});
		$(document).on("click","#prev",function(){t.actions.prev();});
		
		setInterval(function(){
			if(t.tick){
				t.elapsed += 1
			}
			
			t.updatePlayer();
		},1000);
 	},
 	isPlaying: function(){
	 	return (this.state == "play");
 	},
 	elapsedPercent: function(){
	 	var t = this;
 		
 		var percent = 0;
 		
 		if(t.currentsong_length > 0){
	 		percent = (t.elapsed / t.currentsong_length)
 		}
 		percent *= 100;
 		
 		return percent;
 	},
 	updatePlayer: function(){
 		var _percent = this.elapsedPercent() + "%";
 		this.$elapsed.toggleClass("active", this.isPlaying());
 		this.$progressBar.width(_percent);
 		var time_string = "";
 		
 		if(this.elapsed){
	 		time_string = "" + this.elapsed + ""
	 		time_string = time_string.toHHMMSS();
 		}
 		
 		this.$elapsed.find("span.elapsed-time").text(time_string);
 	},
	toggleBtns : function(){
		
		
	},
	actions : {
		play : function(){
			PimmerData.send("play", {},function(data){
				
			});
		},
		pause : function(){
			PimmerData.send("pause");
		},
		stop : function(){
			PimmerData.send("stop");
		},
		next : function(){
			PimmerData.send("next");
		},
		prev : function(){
			PimmerData.send("prev");
		}
	}
}

var PimmerLibrary = {
	init : function(){
		var t = this;
		t.opened = false;
		t.$el = $("#library");
		t.$elBody = t.$el.find("tbody");
		
		$('a[data-toggle="tab"][href=#library-pane]').on('shown.bs.tab', function (e) {
			PimmerData.send("library",{},function(){

				var tracks = PimmerData.data.library["tracks"];
				console.log(tracks);
				t.prepare_add();
				
				for(var i = 0;i < tracks.length; i++){
					var _t = tracks[i];
					t.add_row(_t);
				}
				
				t.finalize_add();
			});
		});
		
		/*
t.$elBody.on("click", ".actions .btn", function(e){
			e.preventDefault();
			var $btn = $(this);
			var _action = $btn.data("action");
			var _data = {
				"id" : $btn.closest("tr").data("file")
			};
			PimmerData.send(_action, _data);
			console.log($btn);
		});
*/
	},
	prepare_add: function(){
		this.$elBody.find('tr').addClass('remove');
	},
	finalize_add: function(){
		this.$elBody.find('tr.remove').remove();
	},
	add_row : function(track, index){
		var t = this;
		var file = track["file"];
		
		var html = ""
		html += "<tr data-file='" + file + "'>";
		html += "<td class='status'><span class='glyphicon glyphicon-volume-up hide'></span></td>";
		html += "<td class='index'></td>";
		html += "<td>" + track["title"]+ "</td>";
		html += "<td>" + track["artist"]+ "</td>";
		html += "<td class='actions'>";
		html += "<a href='#' data-action='add' data-params='file' data-file='" + file +"' class='btn btn-xs btn-success'><span class='glyphicon glyphicon-plus'></span></a>"
		html += "</td>";
		html += "</tr>";
		
		var $row = t.$elBody.find("tr[data-file='" + file + "']");
		
		if($row.length < 1)
			$row = $(html);
			
		
		var current_file = PimmerData.data.currentsong["file"];
		
		$row.toggleClass("active", current_file == file);
		
		$row.removeClass("remove");
		$row.find(".index").html(index + 1);
		t.$elBody.insertAt(index,$row);
	}
}

var PimmerPlaylist = {
	
	init : function(){
		var t = this;
		
		t.$el = $("#playlist");
		
		t.$elBody = t.$el.find("tbody");
		
		
		
		PimmerData.add_callback("playlist", function(){
			
			var tracks = this.data.playlist["tracks"];
			t.prepare_add();
			
			for(var i=0;i<tracks.length;i++){
				var _track = tracks[i];
				t.add_row(_track);
			}
			
			t.finalize_add();
			
		});
	},
	prepare_add: function(){
		this.$elBody.find('tr').addClass('remove');
	},
	finalize_add: function(){
		this.$elBody.find('tr.remove').remove();
	},
	add_row : function(track){
		var t = this;
		var id = track["id"];
		var index = parseInt(track["pos"]);
		var html = ""
		html += "<tr data-id='" + id + "'>";
		html += "<td class='status'><span class='glyphicon glyphicon-volume-up hide'></span></td>";
		html += "<td class='index'></td>";
		html += "<td><a href='#' data-action='playid' data-params='id' data-id='"+ id +"'>" + track["title"]+ "</a></td>";
		html += "<td>" + track["artist"]+ "</td>";
		html += "<td class='actions'>";
		html += "<div class='btn-group pull-right'>";
		html += "<a href='#' data-action='moveid' data-params='from,to' data-from='" + id + "' class='move-up btn btn-xs btn-primary'><span class='glyphicon glyphicon-arrow-up'></span></a>";
		html += "<a href='#' data-action='moveid' data-params='from,to' data-from='" + id + "' class='move-down btn btn-xs btn-primary'><span class='glyphicon glyphicon-arrow-down'></span></a>";
		html += "<a href='#' data-action='deleteid' data-params='id' data-id='"+ id +"' class='btn btn-xs btn-danger'><span class='glyphicon glyphicon-remove'></span></a>";
		html += "</div>";
		html += "</td>";
		html += "</tr>";
		
		var $row = t.$elBody.find("tr[data-id=" + id + "]");
		
		if($row.length < 1)
			$row = $(html);
			
		
		var current_id = PimmerData.data.currentsong["id"];
		
		if(current_id == id){
			
		}
				
		$row.toggleClass("active", current_id == id);
		$row.find(".status .glyphicon").toggleClass("hide", current_id != id);
		
		//data-from='" + index + "' data-to='" + (index - 1) + "'
		$row.find('.move-up').data("to", (index - 1)).toggleClass("disabled", index == 0);
		$row.find('.move-down').data("to", (index + 1)).toggleClass("disabled", (index + 1) == PimmerData.data.playlist.count);
		//console.log($row.find('.move-up').data("to"));
		$row.find(".index").html(index + 1);
		
		$row.removeClass("remove");
		
		t.$elBody.insertAt(index,$row);
	}
}

var PimmerSync = {
	init: function(){
		var t = this;
		
		t.$btn = $("#sync");
		t.syncing = false
		
		PimmerData.add_callback("sync", function(){
			var update = (t.syncing != this.data.sync);
			t.syncing = this.data.sync;
			
			if(update)
				t.updateSync();
		});
		
	}, 
	updateSync: function(){
		var t = this;
		
		t.$btn.toggleClass("disabled", t.syncing);
		if(t.syncing){
			t.$btn.button('loading');
		} else {
			t.$btn.button('reset')
		}
		
		
	}
}

var PimmerPlaylists = {
	init: function(){
		var t = this;
		t.$el = $("#playlists");
		t.last_state = "";
		
		t.$saveForm = $("#save-playlist");
		t.$saveFormBtn = t.$saveForm.find("[type=submit]");
		
		t.$saveForm.on("keyup", "input", function(){
			var $t = $(this);
			t.$saveFormBtn.data("name", $t.val());
			
		});
		
		t.$saveFormBtn.on("click",function(){
			t.$saveForm.find("input").val("");
		});
		
		PimmerData.add_callback("playlists", function(){
			
			var playlists = this.data.playlists["playlists"];
			var last_state = playlists.join(",");
			
			if(t.last_state == last_state)
				return;
			
			t.last_state = last_state;
			
			t.build_list(playlists);
		});
	},
	build_list: function(playlists){
		var t = this;
		
		t.$el.empty();
		
		$(playlists).each(function(){
			var pl = this;
			var html = "";
			html += "<li class='list-group-item'>";
			html += "<a href='#' data-action='clearload' data-params='id' data-id='" + pl + "'>" + pl + "</a>";
			html += "<div class='pull-right btn-group'>";	
			html += "<a href='#' class='btn btn-xs btn-success' data-action='load' data-params='id' data-id='" + pl + "'><span class='glyphicon glyphicon glyphicon-plus'></span></a>";
			html += "<a href='#' class='btn btn-xs btn-primary'><span class='glyphicon glyphicon glyphicon-floppy-open'></span></a>";
			html += "<a href='#' class='btn btn-xs btn-danger' data-prompt='false' data-action='rm' data-params='id' data-id='" + pl + "'><span class='glyphicon glyphicon-remove'></span></a>";
			html += "</div>";
			html += "</li>";
			t.$el.append(html);
		});
	}
}

$(document).ready(function() {
	PimmerPlayer.init();
	PimmerPlaylist.init();
	PimmerLibrary.init();
	PimmerData.init();
	PimmerSync.init();
	PimmerPlaylists.init();
	
	$(document).on("click", "[data-action]", function(e){
			e.preventDefault();
			var $btn = $(this);
			var _prompt = $btn.data("prompt");
			var _action = $btn.data("action");
			var _params = $btn.data("params");
			
			if(_prompt != undefined){
			
				_prompt = (_prompt == "true");

			} else {
				_prompt = true;
			}
			
			if(!_prompt){
				_prompt = confirm("Are you sure?");
			}
			
			if(!_prompt)
				return;
			
			if(_params != undefined){
				var _arg_params = _params.split(",");
				var _args = []
				var _data = {
				};
				
				for(var i=0; i <_arg_params.length; i++){
					var _key = _arg_params[i];
					_data[_key] = $btn.data(_key)
					
					//_args.push($btn.data(_params[i]));	
				}
				if(!jQuery.isEmptyObject(_data)){
					_data["params"] = _params
				}
			}
			PimmerData.send(_action, _data);
	});
});
