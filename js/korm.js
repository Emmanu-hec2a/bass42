// var submitted = false;
 
//     function formSubmitted(event) {
// 		submitted = true;
	
// 		// Change button to 'Sending' state
// 		var submitBtn = document.getElementById('submitBtn');
// 		submitBtn.disabled = true; // Disable the button to prevent multiple submissions
// 		submitBtn.value = 'Sending...';
// 		submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Sending';
//     }

//     function iframeLoaded() {
// 		if (submitted) {
// 	    	submitted = false; // Reset the flag
 
// 	    // Alert the user
// 	    	alert('Your details have been successfully submitted.');
 
// 	    // Reset the button to its original state
// 	    	var submitBtn = document.getElementById('submitBtn');
// 	    	submitBtn.disabled = false; // Re-enable the button
// 	    	submitBtn.value = 'Send Message';
// 	    	submitBtn.innerHTML = 'Send Message';
 
// 	    // Redirect to the home page
// 	    window.location.href = '/';
// 		}
//     }

var submitted = false;
 
    function formSubmitted(event) {
		// event.preventDefault();
		submitted = true;
	
		// Change button to 'Sending' state
		var submitBton = document.getElementById('submitBton');
		submitBton.disabled = true; // Disable the button to prevent multiple submissions
		submitBton.value = 'Submitting...';
		submitBton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Sending';
		// event.target.submit();
	}
	

    function iframeLoaded() {
		if (submitted) {
	    	submitted = false; // Reset the flag
 
	    // Alert the user
	    	alert('Hello Alumni, Thank you for submitting your details');
 
	    // Reset the button to its original state
	    	var submitBton = document.getElementById('submitBton');
	    	submitBton.disabled = false; // Re-enable the button
	    	submitBton.value = 'Submit';
	    	submitBton.innerHTML = 'Submit';
 
	    // Redirect to the home page
	    window.location.href = '#';
		}
    }

