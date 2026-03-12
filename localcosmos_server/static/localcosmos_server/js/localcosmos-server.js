function each(data, onIter, onFinished){

	if (!data){
		onFinished();
	}
	else if( Object.prototype.toString.call( data ) === '[object Array]' || data instanceof Array || Object.prototype.toString.call( data ) === '[object HTMLCollection]') {
		
		var index = -1,
			dataCount = data.length;
		
		var workLoop = function(){
			
			index++;
		
			if (index < dataCount){
			
				var obj = data[index];
			
				onIter(obj, workLoop);
			
			}
			else {
				if (typeof onFinished == 'function'){
					onFinished();
				}
			}
		
		}
	
		workLoop();

	}
	else {
		
		var keys = Object.keys(data);

		if (keys.length > 0){

			var index = -1,
				dataCount = keys.length;

			var workLoop = function(){
				index++;
			
				if (index < dataCount){

					var objname = keys[index];
				
					var obj = data[objname];
				
					onIter(objname, obj, workLoop);
				
				}
				else{
					if (typeof onFinished == 'function'){
						onFinished();
					}
				}
			}
		
			workLoop();
		}
		else {
			onFinished();
		}

	}

}


function hideModal () {
	let modalEl = document.getElementById("Modal");
	if (modalEl){
		let modal = bootstrap.Modal.getOrCreateInstance(modalEl);
		modal.hide();
	}
	/* this might break injected scripts, so maybe we can just leave the content in place and let it be overwritten when the next modal is shown
	let modalContentEl = document.getElementById("ModalContent");
	if (modalContentEl) {
		modalContentEl.replaceChildren();
	}*/
}

function hideLargeModal () {
	let largeModalEl = document.getElementById("LargeModal");
	if (largeModalEl){
		let largeModal = bootstrap.Modal.getOrCreateInstance(largeModalEl);
		largeModal.hide();
	}
	/* this might break injected scripts, so maybe we can just leave the content in place and let it be overwritten when the next modal is shown
	let largeModalContentEl = document.getElementById("LargeModalContent");
	if (largeModalContentEl) {
		largeModalContentEl.replaceChildren();
	}*/
}

function showModal () {
	const modalEl = document.getElementById("Modal");
	if (modalEl){
		let modal = bootstrap.Modal.getOrCreateInstance(modalEl);
		modal.show();
	}
}

function showLargeModal () {
	let largeModalEl = document.getElementById("LargeModal");
	if (largeModalEl){
		let largeModal = bootstrap.Modal.getOrCreateInstance(largeModalEl);
		largeModal.show();
	}
}
