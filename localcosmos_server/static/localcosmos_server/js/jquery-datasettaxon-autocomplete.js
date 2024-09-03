(function($) {
	$.fn.datasettaxonautocomplete = function(options) {

		if (!options.hasOwnProperty("url")){
			throw new Error("taxonautocomplete requires options.url");
		}

		var taxon_input = $( this );

		var no_results_indicator = $("#" + taxon_input.attr('id') + "_no_results");
		
		taxon_input.focusout(function(){
			no_results_indicator.hide();
			taxon_input.val('');
		});

		taxon_input.typeahead({
			autoSelect: false,
			source: function(input_value, process){

				$.ajax({
					type: "GET",
					url: options.url,
					dataType: "json",
					cache: false,
					data: {
						"searchtext": input_value,
					},
					beforeSend : function(){
						no_results_indicator.hide();
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

				if (options.hasOwnProperty("afterSelect") && typeof(options.afterSelect) == 'function'){
					options.afterSelect(item);
				}

			},
			minLength: 3,
			delay: 500
		}); 
	}
}(jQuery));
