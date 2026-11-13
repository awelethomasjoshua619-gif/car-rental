// FAST CARS - Interactive Frontend Logic

document.addEventListener('DOMContentLoaded', function () {
    // Restore the full fleet automatically when a submitted keyword is cleared.
    const vehicleSearchInput = document.getElementById('vehicle-keyword-search');
    const submittedKeyword = new URLSearchParams(window.location.search).get('q');
    if (vehicleSearchInput && submittedKeyword && submittedKeyword.trim()) {
        vehicleSearchInput.addEventListener('input', function () {
            if (!vehicleSearchInput.value.trim()) {
                const searchForm = vehicleSearchInput.form;
                if (searchForm && !searchForm.dataset.submitting) {
                    searchForm.dataset.submitting = 'true';
                    if (typeof searchForm.requestSubmit === 'function') {
                        searchForm.requestSubmit();
                    } else {
                        searchForm.submit();
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------
    // Auto-calculate Total Days & Price on Car Details Booking Form
    // -------------------------------------------------------------
    const fromDateInput = document.getElementById('booking_from_date');
    const toDateInput = document.getElementById('booking_to_date');
    const driverCheckbox = document.getElementById('driver_needed');
    const daysDisplay = document.getElementById('calc_days');
    const totalDisplay = document.getElementById('calc_total_price');
    const dailyPriceElement = document.getElementById('daily_rate_val');

    if (fromDateInput && toDateInput && dailyPriceElement) {
        // Enforce today as minimum pick-up date
        const todayStr = fromDateInput.min || new Date().toISOString().split('T')[0];
        fromDateInput.min = todayStr;
        toDateInput.min = todayStr;

        function updateBookingCalculation() {
            const fromVal = fromDateInput.value;
            const toVal = toDateInput.value;
            const dailyRate = parseFloat(dailyPriceElement.dataset.rate) || 0;
            const driverFeePerDay = parseFloat(dailyPriceElement.dataset.chauffeurFee) || 0;
            const currencyCode = dailyPriceElement.dataset.currency || 'Currency not set';

            if (fromVal && toVal) {
                const date1 = new Date(fromVal);
                const date2 = new Date(toVal);

                if (date2 >= date1) {
                    const diffTime = Math.abs(date2 - date1);
                    let diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    if (diffDays === 0) diffDays = 1; // Minimum 1 day

                    const hasDriver = driverCheckbox && driverCheckbox.checked;
                    const driverTotal = hasDriver ? (driverFeePerDay * diffDays) : 0;
                    const grandTotal = (dailyRate * diffDays) + driverTotal;

                    if (daysDisplay) daysDisplay.textContent = diffDays + (diffDays === 1 ? ' day' : ' days');
                    if (totalDisplay) totalDisplay.textContent = currencyCode + ' ' + grandTotal.toFixed(2);
                } else {
                    if (daysDisplay) daysDisplay.textContent = 'Invalid dates';
                    if (totalDisplay) totalDisplay.textContent = currencyCode + ' 0.00';
                }
            }
        }

        fromDateInput.addEventListener('change', function () {
            toDateInput.min = fromDateInput.value;
            if (toDateInput.value && toDateInput.value < fromDateInput.value) {
                toDateInput.value = fromDateInput.value;
            }
            updateBookingCalculation();
        });

        toDateInput.addEventListener('change', updateBookingCalculation);
        if (driverCheckbox) driverCheckbox.addEventListener('change', updateBookingCalculation);

        // Run initial check
        updateBookingCalculation();
    }

    // -------------------------------------------------------------
    // Star Rating Click Selector for Testimonial Submission
    // -------------------------------------------------------------
    const starPicker = document.querySelectorAll('.star-picker-icon');
    const ratingInput = document.getElementById('selected_rating');

    if (starPicker.length > 0 && ratingInput) {
        starPicker.forEach(star => {
            star.addEventListener('click', function () {
                const rating = parseInt(this.getAttribute('data-value'), 10);
                ratingInput.value = rating;
                starPicker.forEach(s => {
                    const val = parseInt(s.getAttribute('data-value'), 10);
                    if (val <= rating) {
                        s.classList.remove('fa-regular');
                        s.classList.add('fa-solid');
                    } else {
                        s.classList.remove('fa-solid');
                        s.classList.add('fa-regular');
                    }
                });
            });
        });
    }

    // Initialize vehicle gallery keyboard support
    initVehicleGallery();
});

// -------------------------------------------------------------
// Interactive Multi-Angle Vehicle Showcase
// -------------------------------------------------------------
let currentAngleIndex = 0;

function initVehicleGallery() {
    const mainImg = document.getElementById('mainVehicleImage');
    const thumbs = document.querySelectorAll('.angle-thumb');
    if (!mainImg || thumbs.length === 0) return;

    thumbs.forEach(thumb => {
        thumb.addEventListener('click', function () {
            selectVehicleAngle(Number(this.dataset.imageIndex));
        });
    });

    document.addEventListener('keydown', function (e) {
        if (e.target.matches('input, textarea, select, [contenteditable="true"]')) return;
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            changeVehicleAngle(-1);
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            changeVehicleAngle(1);
        }
    });
}

function selectVehicleAngle(index) {
    const mainImg = document.getElementById('mainVehicleImage');
    const angleText = document.getElementById('angleText');
    const thumbs = document.querySelectorAll('.angle-thumb');
    const selectedThumb = thumbs[index];
    if (!mainImg || !selectedThumb) return;

    const url = selectedThumb.dataset.imageUrl;
    const label = selectedThumb.dataset.imageLabel;
    if (!url) return;

    currentAngleIndex = index;

    mainImg.style.opacity = '0.35';
    setTimeout(() => {
        mainImg.src = url;
        mainImg.alt = selectedThumb.querySelector('img')?.alt || `${label} vehicle view`;
        mainImg.style.opacity = '1';
    }, 120);

    if (angleText && label) {
        angleText.textContent = label;
    }

    thumbs.forEach((t, i) => {
        if (i === index) {
            t.classList.add('active');
            t.setAttribute('aria-pressed', 'true');
        } else {
            t.classList.remove('active');
            t.setAttribute('aria-pressed', 'false');
        }
    });
}

function changeVehicleAngle(direction) {
    const thumbs = document.querySelectorAll('.angle-thumb');
    if (thumbs.length === 0) return;

    let nextIndex = currentAngleIndex + direction;
    if (nextIndex < 0) nextIndex = thumbs.length - 1;
    if (nextIndex >= thumbs.length) nextIndex = 0;

    selectVehicleAngle(nextIndex);
}

// Printable Receipt / Invoice Generator
function printInvoice(modalId) {
    const printContent = document.getElementById(modalId).innerHTML;
    const originalContent = document.body.innerHTML;
    document.body.innerHTML = printContent;
    window.print();
    document.body.innerHTML = originalContent;
    window.location.reload();
}
