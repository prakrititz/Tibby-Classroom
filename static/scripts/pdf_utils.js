document.getElementById('add-reference').addEventListener('click', function() {
    document.getElementById('pdf-upload').click();
});

document.getElementById('pdf-upload').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        uploadPDF(file);
    }
});

function uploadPDF(file) {
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload_pdf', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert(data.message);
            // You can update the UI here to show the uploaded file
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while uploading the file.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('view-references').addEventListener('click', function() {
        fetch('/get_pdf_list')
            .then(response => response.json())
            .then(data => {
                const pdfList = document.getElementById('pdf-list');
                if (pdfList) {
                    pdfList.innerHTML = '';
                    data.pdfs.forEach(pdf => {
                        const li = document.createElement('li');
                        const a = document.createElement('a');
                        a.href = `/get_document/${pdf}`;
                        a.textContent = pdf;
                        a.target = '_blank';
                        li.appendChild(a);
                        pdfList.appendChild(li);
                    });
                    document.getElementById('references-modal').style.display = 'block';
                } else {
                    console.error('PDF list element not found');
                }
            });
    });
});

document.querySelector('.close').addEventListener('click', function() {
    document.getElementById('references-modal').style.display = 'none';
});

window.onclick = function(event) {
    if (event.target == document.getElementById('references-modal')) {
        document.getElementById('references-modal').style.display = 'none';
    }
}