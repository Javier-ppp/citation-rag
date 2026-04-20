document.addEventListener('DOMContentLoaded', () => {
    // App Context to share state
    const appContext = {
        currentPdfId: null,
        currentPdfName: null
    };

    const viewer = new PdfViewer('pdf-container-wrapper', 'pdf-canvas', 'text-layer');
    const overlay = new CitationOverlay(appContext);
    const search = new ForwardSearch();

    // Hook viewer events to overlay
    viewer.onPageRendered = (textLayerElement) => overlay.processTextLayer(textLayerElement);

    // Setup Toolbar bindings
    document.getElementById('prev-page').addEventListener('click', () => viewer.onPrevPage());
    document.getElementById('next-page').addEventListener('click', () => viewer.onNextPage());
    document.getElementById('zoom-in').addEventListener('click', () => viewer.zoomIn());
    document.getElementById('zoom-out').addEventListener('click', () => viewer.zoomOut());

    // Setup File Upload
    const uploadInput = document.getElementById('pdf-upload');
    const statusMsg = document.getElementById('upload-status');
    const emptyState = document.getElementById('pdf-empty-state');
    const pdfContainer = document.getElementById('pdf-container');

    uploadInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        statusMsg.textContent = 'Uploading and ingesting...';
        
        try {
            const data = await ApiClient.ingestPdf(file);
            statusMsg.textContent = `Indexed: ${data.num_pages} pages, ${data.num_chunks} chunks.`;
            
            appContext.currentPdfId = data.paper_id;
            appContext.currentPdfName = file.name;
            
            // Load natively for viewing
            const fileUrl = URL.createObjectURL(file);
            emptyState.classList.add('hidden');
            pdfContainer.classList.remove('hidden');
            
            await viewer.loadDocument(fileUrl);
        } catch (error) {
            statusMsg.textContent = 'Ingest failed.';
        }
        
        // Reset input
        uploadInput.value = '';
    });
});
