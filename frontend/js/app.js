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

    // Sidebar Logic (Logo Toggle)
    const libraryPane = document.getElementById('library-pane');
    const libraryList = document.getElementById('library-list');
    document.getElementById('app-logo').addEventListener('click', (e) => {
        e.preventDefault();
        libraryPane.classList.toggle('collapsed');
        // Trigger a fake resize event to help PDF canvas stay centered if needed
        window.dispatchEvent(new Event('resize'));
    });

    // Resize Logic
    const initResizers = () => {
        const leftResizer = document.getElementById('left-resizer');
        const rightResizer = document.getElementById('right-resizer');
        const searchPane = document.querySelector('.search-pane');
        
        const handleDrag = (resizer, target, isRight = false) => {
            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                document.body.style.cursor = 'col-resize';
                resizer.classList.add('active');
                
                const onMouseMove = (moveEvent) => {
                    let newWidth;
                    if (isRight) {
                        newWidth = window.innerWidth - moveEvent.clientX;
                        target.style.flex = `0 0 ${Math.max(200, Math.min(600, newWidth))}px`;
                    } else {
                        newWidth = moveEvent.clientX;
                        target.style.flex = `0 0 ${Math.max(150, Math.min(500, newWidth))}px`;
                    }
                };
                
                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    document.body.style.cursor = 'default';
                    resizer.classList.remove('active');
                    window.dispatchEvent(new Event('resize'));
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        };
        
        handleDrag(leftResizer, libraryPane);
        handleDrag(rightResizer, searchPane, true);
    };
    initResizers();

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
                    document.getElementById('current-paper-display').classList.add('pulsing');
                    setTimeout(() => document.getElementById('current-paper-display').classList.remove('pulsing'), 2000);
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
        
        if (role === 'main') {
            statusMsg.textContent = `Analyzing main paper: ${file.name} (Extracting references)...`;
        } else {
            statusMsg.textContent = `Ingesting: ${file.name}...`;
        }
        
        try {
            const data = await ApiClient.ingestPdf(file, role);
            
            if (role === 'main') {
                statusMsg.textContent = `Indexed: ${data.num_pages} pages, ${data.num_chunks} chunks. Ready.`;
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
            } else {
                statusMsg.textContent = `Completed: ${file.name}`;
            }

            // Refresh library view
            await refreshLibrary();
        } catch (e) {
            console.error('Upload failed details:', e);
            statusMsg.textContent = `Upload failed: ${e.message}`;
        }
    };

    document.getElementById('main-upload').addEventListener('change', (e) => {
        handleUpload(e.target.files[0], 'main');
        e.target.value = ''; // Reset
    });

    document.getElementById('source-upload').addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const total = files.length;
        for (let i = 0; i < total; i++) {
            statusMsg.textContent = `Uploading sources: ${i + 1} of ${total}...`;
            await handleUpload(files[i], 'source');
        }
        statusMsg.textContent = `Finished uploading ${total} papers.`;
        e.target.value = ''; // Reset
    });

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
