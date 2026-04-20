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

    // Sidebar Logic
    const libraryPane = document.getElementById('library-pane');
    const libraryList = document.getElementById('library-list');
    document.getElementById('toggle-library').addEventListener('click', () => {
        libraryPane.classList.toggle('collapsed');
    });

    const refreshLibrary = async () => {
        try {
            const papers = await ApiClient.getPapers();
            libraryList.innerHTML = '';
            papers.forEach(p => {
                const item = document.createElement('div');
                item.className = 'library-item';
                item.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                    <div class="library-item-content" title="${p.filename}">${p.filename}</div>
                `;
                libraryList.appendChild(item);
            });
        } catch (e) {
            console.error('Failed to load library:', e);
        }
    };

    // Load initial library
    refreshLibrary();

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
            
            // Refresh library view
            refreshLibrary();

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
