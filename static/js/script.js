// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {

    // --- Responsive Table Wrapper ---
    const tables = document.querySelectorAll('.content > table');
    tables.forEach(function(table) {
        if (table.parentElement && !table.parentElement.classList.contains('table-responsive-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive-wrapper';
            if (table.parentNode) {
                table.parentNode.insertBefore(wrapper, table);
            }
            wrapper.appendChild(table);
        }
    });

    // --- Custom Sale Modal Logic (Main POS Page) ---
    const modal = document.getElementById('customSaleModal');
    const openModalBtn = document.getElementById('customSaleBtn');
    const closeModalSpan = modal ? modal.querySelector('.close-button') : null;
    const cancelButton = modal ? modal.querySelector('.cancel-button') : null;
    const customSaleForm = document.getElementById('customSaleForm');
    const customProductNameSelect = document.getElementById('custom_product_name');
    const customItemNameTextGroup = document.getElementById('custom_item_name_text_group');
    const customItemNameTextInput = document.getElementById('custom_item_name_text_manual');

    function openCustomSaleModal() {
        if (modal) {
            modal.style.display = 'block';
            if(customSaleForm) {
               const priceInput = customSaleForm.querySelector('#custom_price');
               const qtyInput = customSaleForm.querySelector('#custom_quantity');
               if(priceInput) priceInput.value = ''; 
               if(qtyInput) qtyInput.value = '1'; 
               if(customProductNameSelect){ 
                   customProductNameSelect.selectedIndex = 0; 
                   if(customItemNameTextGroup) customItemNameTextGroup.style.display = 'none';
                   if(customItemNameTextInput) customItemNameTextInput.value = ''; 
                   customProductNameSelect.setAttribute('name', 'custom_product_name');
                   if(customItemNameTextInput) customItemNameTextInput.removeAttribute('name');
               }
            }
            if (customProductNameSelect) {
                customProductNameSelect.focus();
            }
        }
    }

    function closeCustomSaleModal() {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    if (openModalBtn) {
        openModalBtn.addEventListener('click', openCustomSaleModal);
    }
    if (closeModalSpan) {
        closeModalSpan.addEventListener('click', closeCustomSaleModal);
    }
    if (cancelButton) {
        cancelButton.addEventListener('click', closeCustomSaleModal);
    }
    window.addEventListener('click', function(event) {
        if (modal && event.target == modal) { 
            closeCustomSaleModal();
        }
    });

    if (customSaleForm) {
        customSaleForm.addEventListener('submit', function(event) {
            const priceInput = customSaleForm.querySelector('#custom_price');
            const quantityInput = customSaleForm.querySelector('#custom_quantity');
            let isValid = true;

            if (customProductNameSelect && customProductNameSelect.value === 'Custom Item/Service') {
                if (!customItemNameTextInput || customItemNameTextInput.value.trim() === '') {
                    alert('Please enter a name for the custom item/service.');
                    isValid = false;
                    if (customItemNameTextInput) customItemNameTextInput.focus();
                }
            } else if (customProductNameSelect && customProductNameSelect.value.trim() === '') {
                 alert('Please select a product or choose "Custom Item/Service".');
                 isValid = false;
                 if(customProductNameSelect) customProductNameSelect.focus();
            }

            if (isValid && (!priceInput || priceInput.value === '' || parseFloat(priceInput.value) < 0)) {
                alert('Please enter a valid non-negative price.');
                isValid = false;
                if(priceInput) priceInput.focus();
            }
            if (isValid && (!quantityInput || quantityInput.value === '' || parseInt(quantityInput.value) <= 0)) {
                 alert('Please enter a valid positive quantity.');
                 isValid = false;
                 if(quantityInput) quantityInput.focus();
            }

            if (!isValid) {
                event.preventDefault(); 
            }
        });
    }

    if (customProductNameSelect && customItemNameTextGroup && customItemNameTextInput) {
        customProductNameSelect.addEventListener('change', function() {
            if (this.value === 'Custom Item/Service') { 
                customItemNameTextGroup.style.display = 'block'; 
                customItemNameTextInput.setAttribute('name', 'custom_product_name_override'); 
                customProductNameSelect.removeAttribute('name'); 
                customItemNameTextInput.focus();
            } else { 
                customItemNameTextGroup.style.display = 'none'; 
                customItemNameTextInput.removeAttribute('name'); 
                customProductNameSelect.setAttribute('name', 'custom_product_name'); 
            }
        });
        // Initial check for page load state
        if (customProductNameSelect.value === 'Custom Item/Service') {
             customItemNameTextGroup.style.display = 'block';
             customItemNameTextInput.setAttribute('name', 'custom_product_name_override');
             customProductNameSelect.removeAttribute('name');
        }
    }

    const navToggle = document.querySelector('.nav-toggle'); 
    const navLinksUl = document.querySelector('.main-nav ul.nav-links'); 

    if (navToggle && navLinksUl) {
        navToggle.addEventListener('click', () => {
            navLinksUl.classList.toggle('nav-open'); 
            const isExpanded = navLinksUl.classList.contains('nav-open');
            navToggle.setAttribute('aria-expanded', isExpanded); 
            document.body.classList.toggle('nav-active', isExpanded); 
        });
    }

    const dropdownToggles = document.querySelectorAll('.nav-item-dropdown > .dropdown-toggle-link');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(event) {
            event.preventDefault(); 
            const dropdownItemLi = this.parentElement; 

            document.querySelectorAll('.nav-item-dropdown.open').forEach(openDropdown => {
                if (openDropdown !== dropdownItemLi) { 
                    openDropdown.classList.remove('open');
                    const otherToggleLink = openDropdown.querySelector('.dropdown-toggle-link');
                    if (otherToggleLink) {
                        otherToggleLink.setAttribute('aria-expanded', 'false');
                    }
                }
            });

            dropdownItemLi.classList.toggle('open');
            const isDropdownOpen = dropdownItemLi.classList.contains('open');
            this.setAttribute('aria-expanded', isDropdownOpen); 
        });
    });

    document.addEventListener('click', function(event) {
        const openDropdown = document.querySelector('.nav-item-dropdown.open');
        if (openDropdown && !openDropdown.contains(event.target)) {
            if (navToggle && navToggle.contains(event.target)) {
                return;
            }
            openDropdown.classList.remove('open');
            const toggleLink = openDropdown.querySelector('.dropdown-toggle-link');
            if (toggleLink) {
                toggleLink.setAttribute('aria-expanded', 'false');
            }
        }
    });

    function initializeChart(canvasId) {
        const ctx = document.getElementById(canvasId); 
        if (!ctx) {
            return; 
        }

        const contextForMessage = ctx.getContext('2d');

        function displayCanvasMessage(message, color = '#888') {
            contextForMessage.clearRect(0, 0, ctx.width, ctx.height); 
            contextForMessage.textAlign = 'center';
            contextForMessage.fillStyle = color; 
            contextForMessage.font = '16px Arial'; 
            contextForMessage.fillText(message, ctx.width / 2, ctx.height / 2);
        }

        if (typeof Chart === 'undefined') {
            console.error("Chart.js library not loaded! Make sure it's included in your base.html.");
            displayCanvasMessage('Chart library not loaded.', '#cc0000');
            return; 
        }
        
        let existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }

        let labels, values;
        const rawLabels = ctx.dataset.labels; // Get the string from data-labels
        const rawValues = ctx.dataset.values; // Get the string from data-values

        console.log(`Chart '${canvasId}' Attempting to parse:`);
        console.log(`  Raw data-labels: '${rawLabels}'`);
        console.log(`  Raw data-values: '${rawValues}'`);

        // Check for undefined or truly empty strings for labels
        if (typeof rawLabels === 'undefined' || rawLabels.trim() === '') {
            console.warn(`Chart '${canvasId}': data-labels attribute is missing, empty, or undefined.`);
            labels = []; // Default to empty array
        } else {
            try {
                labels = JSON.parse(rawLabels);
            } catch (eLabels) {
                console.error(`Error parsing data-labels for chart '${canvasId}'. Content:`, rawLabels, `Error:`, eLabels);
                displayCanvasMessage('Error loading chart labels (parsing).', '#f00');
                return; 
            }
        }

        // Check for undefined or truly empty strings for values
        if (typeof rawValues === 'undefined' || rawValues.trim() === '') {
            console.warn(`Chart '${canvasId}': data-values attribute is missing, empty, or undefined.`);
            values = []; // Default to empty array
        } else {
            try {
                values = JSON.parse(rawValues);
            } catch (eValues) {
                console.error(`Error parsing data-values for chart '${canvasId}'. Content:`, rawValues, `Error:`, eValues);
                displayCanvasMessage('Error loading chart values (parsing).', '#f00');
                return;
            }
        }
        
        // Check if Flask passed an explicit error message for this chart
        const flaskErrorMessage = ctx.dataset.errorMessage;
        if (flaskErrorMessage) {
            console.error(`Error passed from Flask for chart '${canvasId}': ${flaskErrorMessage}`);
            displayCanvasMessage(flaskErrorMessage, '#f00');
            return;
        }
        
        // If after attempting to parse, we still have no data (e.g., Flask sent empty lists that parsed correctly)
        if (labels.length === 0 || values.length === 0) {
             // Check if there was a flask error message. If so, that takes precedence.
            if (!flaskErrorMessage) { // Only show "No data" if no specific Flask error was already shown
                displayCanvasMessage('No data available for this period.');
            }
            return;
        }

        // If we've reached here, data should be valid and parsed
        try {
            const chartType = ctx.dataset.chartType || 'bar';
            const chartTitle = ctx.dataset.title || 'Sales Chart';
            const datasetLabel = ctx.dataset.label || 'Sales';
            const bgColor = ctx.dataset.bgColor || 'rgba(141, 182, 0, 0.6)'; 
            const borderColor = ctx.dataset.borderColor || 'rgba(106, 138, 0, 1)';
            const xAxisLabel = ctx.dataset.xAxisLabel || ''; 

            new Chart(ctx.getContext('2d'), {
                type: chartType,
                data: {
                    labels: labels,
                    datasets: [{
                        label: datasetLabel,
                        data: values,
                        backgroundColor: bgColor,
                        borderColor: borderColor,
                        borderWidth: 1
                    }]
                },
                options: { 
                    responsive: true,
                    maintainAspectRatio: false, 
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) { 
                                    return '₱' + value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0});
                                }
                            }
                        },
                        x: {
                            title: {
                                display: !!xAxisLabel, 
                                text: xAxisLabel
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: chartTitle
                        },
                        tooltip: {
                             callbacks: {
                                label: function(context) { 
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += '₱' + context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                    }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });
        } catch (eChart) {
            console.error(`Error creating chart instance for '${canvasId}':`, eChart);
            displayCanvasMessage('Error rendering chart.', '#f00');
        }
    }

    initializeChart('weeklySalesChart');
    initializeChart('monthlySalesChart');

}); // End DOMContentLoaded
