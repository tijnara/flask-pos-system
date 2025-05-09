// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {

    // --- Responsive Table Wrapper ---
    // Wraps tables found directly within '.content' for horizontal scrolling on small screens
    const tables = document.querySelectorAll('.content > table');
    tables.forEach(function(table) {
        // Check if the table is already wrapped to avoid double-wrapping
        if (table.parentElement && !table.parentElement.classList.contains('table-responsive-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive-wrapper';
            // Insert the wrapper before the table in the DOM
            if (table.parentNode) {
                table.parentNode.insertBefore(wrapper, table);
            }
            // Move the table into the new wrapper
            wrapper.appendChild(table);
        }
    });

    // --- Custom Sale Modal Logic ---
    const modal = document.getElementById('customSaleModal');
    const openModalBtn = document.getElementById('customSaleBtn');
    // Ensure modal exists before trying to query inside it
    const closeModalSpan = modal ? modal.querySelector('.close-button') : null;
    const cancelButton = modal ? modal.querySelector('.cancel-button') : null;
    const customSaleForm = document.getElementById('customSaleForm');

    // Function to open the modal
    function openModal() {
        if (modal) {
            modal.style.display = 'block';
            // Optional: Clear form fields when opening
            if(customSaleForm) {
               const priceInput = customSaleForm.querySelector('#custom_price');
               const qtyInput = customSaleForm.querySelector('#custom_quantity');
               const nameInput = customSaleForm.querySelector('#custom_product_name'); // Changed from #custom_product_name_select
               
               if(priceInput) priceInput.value = ''; // Clear price
               if(qtyInput) qtyInput.value = '1'; // Reset quantity to 1
               
               // If it's a select dropdown for product name, reset to the first (disabled) option
               if(nameInput && nameInput.tagName === 'SELECT'){
                   nameInput.selectedIndex = 0; 
               } else if (nameInput) { // If it's a text input
                   nameInput.value = 'Custom Item'; // Reset name for text input
               }
            }
            // Optional: Focus the first input field (product name or select)
            const firstInput = customSaleForm ? (customSaleForm.querySelector('#custom_product_name') || customSaleForm.querySelector('input[type="number"]')) : null;
            if (firstInput) {
                firstInput.focus();
                if(firstInput.tagName !== 'SELECT' && firstInput.select) { // Only call select() on text inputs
                    firstInput.select(); 
                }
            }
        }
    }

    // Function to close the modal
    function closeModal() {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Event listener for the "Custom Sale" button to open modal
    if (openModalBtn) {
        openModalBtn.addEventListener('click', openModal);
    }

    // Event listener for the close span (X) to close modal
    if (closeModalSpan) {
        closeModalSpan.addEventListener('click', closeModal);
    }

    // Event listener for the Cancel button to close modal
    if (cancelButton) {
        cancelButton.addEventListener('click', closeModal);
    }

    // Event listener to close modal if user clicks anywhere on the dark overlay
    window.addEventListener('click', function(event) {
        if (modal && event.target == modal) { // Check if modal exists and target is the modal background
            closeModal();
        }
    });

    // Optional: Client-side validation before submitting custom sale form
    if (customSaleForm) {
        customSaleForm.addEventListener('submit', function(event) {
            const priceInput = customSaleForm.querySelector('#custom_price');
            const quantityInput = customSaleForm.querySelector('#custom_quantity');
            const nameInput = customSaleForm.querySelector('#custom_product_name'); // This could be a select or input
            let isValid = true;

            if (!nameInput || nameInput.value.trim() === '') {
                 alert('Please select or enter a product name.');
                 isValid = false;
                 if(nameInput) nameInput.focus();
            }
            else if (!priceInput || priceInput.value === '' || parseFloat(priceInput.value) < 0) {
                alert('Please enter a valid non-negative price.');
                isValid = false;
                if(priceInput) priceInput.focus();
            }
            else if (!quantityInput || quantityInput.value === '' || parseInt(quantityInput.value) <= 0) {
                 alert('Please enter a valid positive quantity.');
                 isValid = false;
                 if(quantityInput) quantityInput.focus();
            }

            if (!isValid) {
                event.preventDefault(); // Stop form submission if validation fails
            }
            // If using AJAX, you would preventDefault always and handle submission here.
            // For standard POST, we let it submit if valid. The modal will close implicitly
            // when the page reloads after the POST request is handled by Flask.
        });
    }

    // --- Mobile Navigation Toggle ---
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('nav-open'); // Toggle class to show/hide
            // Toggle aria-expanded attribute for accessibility
            const isExpanded = navLinks.classList.contains('nav-open');
            navToggle.setAttribute('aria-expanded', isExpanded);
            // Toggle class on body to prevent scrolling when nav is open (optional)
            // You would need to add 'overflow: hidden;' to 'body.nav-active' in your CSS
            document.body.classList.toggle('nav-active', isExpanded); 
        });
    }

}); // End DOMContentLoaded
