var positionmanager = {

	onMoveForward : function(){

		const currentId = this.getAttribute("data-targetid");

		const current = document.getElementById(currentId);
		const tagname = current.tagName;
		const previous = current.previousElementSibling;

		if (previous != null && previous.tagName == tagname){
			current.parentNode.insertBefore(current, previous);
		}

		positionmanager.store_positions(current);
	},

	onMoveBack : function(){

		const currentId = this.getAttribute("data-targetid");

		const current = document.getElementById(currentId);
		const tagname = current.tagName;
		const next = current.nextElementSibling;

		if (next != null && next.tagName == tagname){
			current.parentNode.insertBefore(next, current);
		}

		positionmanager.store_positions(current);
	},

	store_positions : function(itemElement){

		const parentElement = itemElement.parentElement;

		const order = [];

		// iterate over all children of parentElement, and push their data-object-id into order[]
		const children = parentElement.children;

		for (let i = 0; i < children.length; i++) {
			const child = children[i];
			const dataObjectId = child.getAttribute("data-object-id");
			if (dataObjectId.indexOf("-") != -1) {
				order.push(dataObjectId);
			} else {
				order.push(parseInt(dataObjectId));
			}
		}

		const url = parentElement.getAttribute("data-store-positions-url");

		$.post(url, {"order":JSON.stringify(order)}, function(){
		});
	},
	
	// get_content_fn is a function that returns the text content which is the parameter for sorting
	// alphabetical sorting does not work across languages
	sort_alphabetically : function(container_id, get_text_content_fn){
		// get all elements of container
		var container = document.getElementById(container_id);
		// get all element children, not descendants
		var elements = container.children;
		
		var sorted_elements = [];
		
		// iterate over each child, and insert it into a new list which is alphabetically sorted
		for (let e=0; e<elements.length; e++){
			
			let element = elements[e];
			
			let text_content = get_text_content_fn(element);
			
			if (sorted_elements.length == 0){
				sorted_elements.push(element);
			}
			else {
				
				let found_position = false;
				
				// iterate over all sorted_elements[]
				for (let s=0; s<sorted_elements.length; s++){
					let sorted_element = sorted_elements[s];
					let sorted_element_text_content = get_text_content_fn(sorted_element);
					
					let is_positioned_before = text_content < sorted_element_text_content;
					
					if (is_positioned_before == true){
						
						let insert_index = sorted_elements.indexOf(sorted_element);
						sorted_elements.splice(insert_index, 0, element);
						found_position = true;
						
						break;
					}					
				}
				
				if (found_position == false){
					sorted_elements.push(element);
				}
			}
		}
		
		// sort in UI
		for (let e=0; e<sorted_elements.length; e++){
			let element = sorted_elements[e];
			
			if (e == 0){
				$(element).prependTo($(container));
			}
			else if (e == sorted_elements.length -1){
				$(element).appendTo($(container));
			}
			else {
				let previous_element = sorted_elements[e-1]
				$(element).insertAfter($(previous_element));
				
			}
		}
		
		// store positions
		var element = sorted_elements[0];
		positionmanager.store_positions(element);
	}

};
