(function($) {
	$.fn.userautocomplete = function(url) {

		var username_input = $( this );

		var no_results_indicator = $("#id_search_user_no_results");

		username_input.focusout(function(){
			no_results_indicator.hide();
			username_input.val('');
		});

		username_input.typeahead({
			source: function(input_value, process){

				$.ajax({
					type: "GET",
					url: url,
					dataType: "json",
					cache: false,
					data: {
						"searchtext": input_value
					},
					success: function (data) {

						if (data.length == 0){
							no_results_indicator.show();
						}
						else {
							no_results_indicator.hide();
							process(data);
						}
					},
					error: function(){
						
					}
				});
			}, 
			afterSelect : function(item){

				$.get(item.edit_role_url, function(html){
					$("#ModalContent").html(html);
					ajaxify("ModalContent");
				});

			},
            autoSelect: false,
			minLength: 3,
			delay: 300
		}); 
	}
}(jQuery));
