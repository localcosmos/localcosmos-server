"use strict";

function ajaxify(container_id){

	// support both id and element
	// not all parent elements of a form have an id
	if (typeof container_id == "string"){
		var container = $("#" + container_id);
	}
	else {
		var container = container_id;
	}	

	// xhr links are AJAX REQUIRED and define a target
	container.find("a.xhr").on("click", function(ev){
		ev.preventDefault();
		var link = $(this);

		if (link.attr("data-url")){
			var url = link.attr("data-url");
		}
		else {
			var url = link.attr("href");
		}

		$.get(url, function(html){
			var target_id = link.attr("ajax-target");
			$("#" + target_id).html(html);
			ajaxify(target_id);
		});
	});

	container.find("button.xhr").on("click", function(ev){
		ev.preventDefault();
		var link = $(this);
		$.get(link.attr("data-url"), function(html){
			var target_id = link.attr("ajax-target");
			$("#" + target_id).html(html);
			ajaxify(target_id);
		});
	});

	// advanced xhr handling

	// xhr forms are AJAX REQUIRED and wont display correctly if used without ajax
	container.find("form.xhr").on("submit", function(ev){
		ev.preventDefault();
		
		var form = $(this);

		if (form.attr("ajax-target")){
			var formcontainer = $("#" + form.attr("ajax-target"));
		}
		else {
			var formcontainer = form.parent();
		}

		var submit_button = form.find('button[type=submit]'),
			enctype = form.attr("enctype");
		
		if (enctype == "multipart/form-data"){
			var contentType = false;
			var processData = false;

			/* this needs updating to the lates ckeditor
			for ( instance in CKEDITOR.instances ) {
				CKEDITOR.instances[instance].updateElement();
			}*/

			var data = new FormData( this );
			
		}
		else {
			var data = form.serialize();
			var contentType = 'application/x-www-form-urlencoded; charset=UTF-8';
			var processData = true;
		}

		submit_button.attr('disabled','disabled');

		$.ajax({
			type: form.attr('method'),
			url: form.attr('action'),
			cache: false,
			contentType: contentType,
			processData: processData,
			data: data,
			success : function(response){
				formcontainer.html(response);
			},
			complete : function(response){
				ajaxify(formcontainer);
			}
		});
	});
}
