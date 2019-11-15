function AjaxFileInput(event){

	var file_field = event.target;

	if (file_field.hasAttribute("data-url")){
		var url = file_field.getAttribute("data-url");
	}
	else {
		// get the url from the form
		alert("not implemented")
	}	

	var field_id = file_field.id;

	var formData = new FormData();

	formData.append(file_field.name, file_field.files[0]);
	
	$.ajax(url, {
		type: "POST",
		processData: false,
		contentType: false,
		data: formData,
		success : function(html){

			var new_node = document.createElement("div");
			new_node.innerHTML = html;

			new_node.getElementsByTagName("input")[0].addEventListener("change", AjaxFileInput);

			// replace the current input with the new one
			var old_field_container_id = "field-" + field_id + "-container";
			
			var old_field_container = document.getElementById(old_field_container_id);

			var replacedNode = old_field_container.parentNode.replaceChild(new_node, old_field_container);

			ajaxify(old_field_container_id);
		}
	});

}

function AjaxFileInputDelete(event){
	var button = event.target;
	
	var url = button.getAttribute("data-url");
	var target = button.getAttribute("ajax-target");

	$.get(url, function(html){
		$("#" + target).html(html);
		ajaxify(target);
	});
}
