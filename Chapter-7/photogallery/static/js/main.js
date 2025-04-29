document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Form validation for create listing
    const createListingForm = document.getElementById('createListingForm');
    if (createListingForm) {
        createListingForm.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = createListingForm.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    }
    
    // Image preview for file uploads
    const imageUpload = document.getElementById('images');
    if (imageUpload) {
        imageUpload.addEventListener('change', function() {
            const files = this.files;
            const previewContainer = document.getElementById('imagePreview');
            
            if (!previewContainer) return;
            
            previewContainer.innerHTML = '';
            
            if (files.length > 10) {
                alert('You can upload a maximum of 10 images.');
                this.value = '';
                return;
            }
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                if (!file.type.match('image.*')) continue;
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.className = 'img-thumbnail m-1';
                    img.style.maxHeight = '100px';
                    previewContainer.appendChild(img);
                }
                reader.readAsDataURL(file);
            }
        });
    }
});