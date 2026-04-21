class PdfViewer {
    constructor(containerId, canvasId, textLayerId) {
        this.container = document.getElementById(containerId);
        this.canvas = document.getElementById(canvasId);
        this.textLayer = document.getElementById(textLayerId);
        this.ctx = this.canvas.getContext('2d', { alpha: false });
        
        this.pdfDoc = null;
        this.pageNum = 1;
        this.pageRendering = false;
        this.pageNumPending = null;
        this.scale = 1.2;
        
        // Callbacks
        this.onPageRendered = null;
    }

    async loadDocument(url) {
        try {
            this.pdfDoc = await pdfjsLib.getDocument(url).promise;
            document.getElementById('page-count').textContent = this.pdfDoc.numPages;
            this.pageNum = 1; // Reset to first page
            this.renderPage(this.pageNum);
        } catch (error) {
            console.error('Error loading PDF:', error);
            alert('Failed to load PDF.');
        }
    }

    async loadPdf(data) {
        try {
            this.pdfDoc = await pdfjsLib.getDocument({ data: data }).promise;
            document.getElementById('page-count').textContent = this.pdfDoc.numPages;
            this.pageNum = 1; // Reset to first page
            this.renderPage(this.pageNum);
        } catch (error) {
            console.error('Error loading PDF from data:', error);
            alert('Failed to render PDF.');
        }
    }

    async renderPage(num) {
        this.pageRendering = true;
        
        try {
            const page = await this.pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: this.scale });
            
            // Setup canvas
            this.canvas.height = viewport.height;
            this.canvas.width = viewport.width;
            
            // Render PDF page to canvas
            const renderContext = {
                canvasContext: this.ctx,
                viewport: viewport
            };
            
            await page.render(renderContext).promise;
            
            // Setup text layer
            this.textLayer.style.left = this.canvas.offsetLeft + 'px';
            this.textLayer.style.top = this.canvas.offsetTop + 'px';
            this.textLayer.style.height = viewport.height + 'px';
            this.textLayer.style.width = viewport.width + 'px';
            
            // Clear old text layer
            this.textLayer.innerHTML = '';
            
            const textContent = await page.getTextContent();
            
            // Render text layer
            await pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: this.textLayer,
                viewport: viewport,
                textDivs: []
            }).promise;
            
            this.pageRendering = false;
            
            // Trigger callback for overlays
            if (this.onPageRendered) {
                this.onPageRendered(this.textLayer, textContent.items);
            }
            
            if (this.pageNumPending !== null) {
                this.renderPage(this.pageNumPending);
                this.pageNumPending = null;
            }
        } catch (error) {
            console.error('Error rendering page:', error);
            this.pageRendering = false;
        }
        
        document.getElementById('page-num').textContent = num;
    }

    queueRenderPage(num) {
        if (this.pageRendering) {
            this.pageNumPending = num;
        } else {
            this.renderPage(num);
        }
    }

    onPrevPage() {
        if (this.pageNum <= 1) return;
        this.pageNum--;
        this.queueRenderPage(this.pageNum);
    }

    onNextPage() {
        if (this.pageNum >= this.pdfDoc.numPages) return;
        this.pageNum++;
        this.queueRenderPage(this.pageNum);
    }
    
    zoomIn() {
        this.scale += 0.2;
        document.getElementById('zoom-val').textContent = Math.round(this.scale * 100) + '%';
        this.queueRenderPage(this.pageNum);
    }
    
    zoomOut() {
        if (this.scale <= 0.4) return;
        this.scale -= 0.2;
        document.getElementById('zoom-val').textContent = Math.round(this.scale * 100) + '%';
        this.queueRenderPage(this.pageNum);
    }
}
