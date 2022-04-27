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
