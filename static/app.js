const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const dropText = document.getElementById('dropText');
const uploadForm = document.getElementById('uploadForm');
const status = document.getElementById('status');
const generateBtn = document.querySelector('.generate-btn');

// Prevenir comportamiento por defecto del drag and drop
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Highlight drop area cuando arrastra archivos
['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropArea.classList.add('dragover');
}

function unhighlight(e) {
    dropArea.classList.remove('dragover');
}

// Handle drop
dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    fileInput.files = files;
    handleFiles(files);
}

// Handle click para seleccionar archivo
dropArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        
        // Verificar que sea imagen
        if (!file.type.startsWith('image/')) {
            alert('Por favor, sube una imagen');
            return;
        }

        // Mostrar preview
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            dropText.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

// Manejar submit del formulario
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!fileInput.files.length) {
        alert('Por favor, selecciona una imagen');
        return;
    }

    const formData = new FormData();
    formData.append('image', fileInput.files[0]);

    // Mostrar estado de carga
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generando...';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Mostrar éxito
            uploadForm.style.display = 'none';
            status.style.display = 'block';

            // Auto-download después de 1 segundo
            setTimeout(() => {
                window.location.href = '/download';
            }, 1000);
        } else {
            alert('Error al generar el skybox');
            resetForm();
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error en la conexión');
        resetForm();
    }
});

// Descargar skybox
document.getElementById('downloadBtn').addEventListener('click', () => {
    window.location.href = '/download';
});

function resetForm() {
    generateBtn.disabled = false;
    generateBtn.textContent = '✨ Generar Skybox';
    fileInput.value = '';
    preview.style.display = 'none';
    dropText.style.display = 'block';
    status.style.display = 'none';
    uploadForm.style.display = 'flex';
}

// Permitir resetear si quieres subir otra imagen
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && status.style.display !== 'none') {
        resetForm();
    }
});
