document.addEventListener('DOMContentLoaded', () => {
    try {
        initApp();
    } catch (e) {
        console.error('Critical initialization error:', e);
    }
});

function initApp() {
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
    document.getElementById('toggle-library').addEventListener('click', (e) => {
        e.preventDefault();
        libraryPane.classList.toggle('collapsed');
    });

    const refreshLibrary = async () => {
        try {
            const papers = await ApiClient.getPapers();
            libraryList.innerHTML = '';
            papers.forEach(p => {
                const item = document.createElement('div');
                item.className = 'library-item';
                if (p.status === 'missing') item.classList.add('missing');
                
                const roleClass = p.role === 'main' ? 'main' : 'source';
                const refNumText = p.ref_number ? `<span class="ref-num">[${p.ref_number}]</span> ` : '';
                const displayText = p.status === 'missing' ? p.title : p.filename;
                const statusBadge = p.status === 'unlinked' ? '<span class="status-badge unlinked">Unlinked</span>' : '';
                
                item.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                    <div class="library-item-content" title="${displayText}">
                        ${refNumText}${displayText} 
                        <span class="role-badge ${roleClass}">${p.role}</span>
                        ${statusBadge}
                    </div>
                `;
                libraryList.appendChild(item);

                // Update current paper display if this is the main paper
                if (p.role === 'main') {
                    document.getElementById('current-paper-display').textContent = p.filename;
                }
            });
        } catch (e) {
            console.error('Failed to load library:', e);
        }
    };

    // Load initial library
    refreshLibrary();

    // Setup Toolbar bindings
    document.getElementById('prev-page').addEventListener('click', (e) => { e.preventDefault(); viewer.onPrevPage(); });
    document.getElementById('next-page').addEventListener('click', (e) => { e.preventDefault(); viewer.onNextPage(); });
    document.getElementById('zoom-in').addEventListener('click', (e) => { e.preventDefault(); viewer.zoomIn(); });
    document.getElementById('zoom-out').addEventListener('click', (e) => { e.preventDefault(); viewer.zoomOut(); });

    // Setup File Upload
    const statusMsg = document.getElementById('upload-status');
    const emptyState = document.getElementById('pdf-empty-state');
    const pdfContainer = document.getElementById('pdf-container');

    const handleUpload = async (file, role) => {
        if (!file) return;
        statusMsg.textContent = `Ingesting ${role} paper...`;
        
        try {
            const data = await ApiClient.ingestPdf(file, role);
            statusMsg.textContent = `Indexed: ${data.num_pages} pages, ${data.num_chunks} chunks.`;

            // CRITICAL: Clear input so same file can be re-selected later
            if (role === 'main') {
                document.getElementById('main-upload').value = '';
            } else {
                document.getElementById('source-upload').value = '';
            }
            
            // Refresh library view
            await refreshLibrary();

            if (role === 'main') {
                appContext.currentPdfId = data.paper_id;
                appContext.currentPdfName = file.name;
                
                // Show in viewer
                emptyState.classList.add('hidden');
                pdfContainer.classList.remove('hidden');
                
                const reader = new FileReader();
                reader.onload = (e) => {
                    try {
                        viewer.loadPdf(e.target.result);
                    } catch (err) {
                        console.error('PDF view error:', err);
                        statusMsg.textContent = 'Render failed.';
                    }
                };
                reader.readAsArrayBuffer(file);
            }
        } catch (e) {
            console.error('Upload failed details:', e);
            statusMsg.textContent = `Upload failed: ${e.message}`;
        }
    };

    document.getElementById('main-upload').addEventListener('change', (e) => handleUpload(e.target.files[0], 'main'));
    document.getElementById('source-upload').addEventListener('change', (e) => handleUpload(e.target.files[0], 'source'));

    document.getElementById('reset-session').addEventListener('click', async (e) => {
        e.preventDefault();
        
        // Confirmation dialog (stays up until clicked)
        const ok = confirm('Are you sure you want to reset the entire session? This will delete all papers.');
        if (!ok) return;
        
        try {
            statusMsg.textContent = 'Resetting session...';
            await ApiClient.resetSession();
            statusMsg.textContent = 'Session reset successfully.';
            
            // Clear viewer state
            appContext.currentPdfId = null;
            appContext.currentPdfName = null;
            
            document.getElementById('current-paper-display').textContent = 'No Paper Loaded';
            pdfContainer.classList.add('hidden');
            emptyState.classList.remove('hidden');
            
            // Clear library
            await refreshLibrary();

            // CRITICAL: Clear file inputs so same file can be re-selected
            document.getElementById('main-upload').value = '';
            document.getElementById('source-upload').value = '';
        } catch (e) {
            console.error('Reset failed details:', e);
            statusMsg.textContent = `Reset failed: ${e.message}`;
        }
    });
}
