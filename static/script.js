document.getElementById('scanBarcodeCard').addEventListener('click', function () {
    // Trigger the barcode scanning functionality
    document.getElementById('startScan').click();
});

document.getElementById('startScan').addEventListener('click', function () {
    // Show the scanner when "Start Scan and Scrape" is clicked
    document.getElementById('scanner-container').style.display = 'block';  // Show video container
    this.style.display = 'none';  // Hide the start scan button

    // Scroll to the camera section
    document.getElementById('scanner-container').scrollIntoView({ behavior: 'smooth' });

    (async function() {
        try {
            // WebAssembly polyfill for BarcodeDetector in some browsers
            if (!window['BarcodeDetector'] || !BarcodeDetector.getSupportedFormats) {
                window['BarcodeDetector'] = barcodeDetectorPolyfill.BarcodeDetectorPolyfill;
            }

            // Access the video element
            const video = document.querySelector('video');

            // Get a stream for the rear camera
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });

            // Set the video stream to the video element
            video.srcObject = stream;

            // Define the supported barcode formats
            const barcodeDetector = new BarcodeDetector({
                formats: ["ean_13", "ean_8", "upc_a", "upc_e"]
            });

            // Start video stream and detect barcodes
            video.play();

            // Infinite loop to detect barcodes
            while (true) {
                try {
                    // Detect barcodes in the video frame
                    const barcodes = await barcodeDetector.detect(video);

                    if (barcodes.length === 0) {
                        // No barcode found, wait 50 ms and try again
                        await new Promise(resolve => setTimeout(resolve, 50));
                        continue;
                    }

                    // Extract the barcode value
                    const barcodeValue = barcodes[0].rawValue;

                    // Notify the user with an alert
                    alert(`Barcode scanned: ${barcodeValue}`);

                    // Show the loading overlay after the alert is acknowledged
                    document.getElementById('loadingOverlay').style.display = 'flex';

                    // Notify the user with vibration
                    navigator.vibrate(200);

                    // Stop the video stream and hide the video container
                    stream.getTracks().forEach(track => track.stop());
                    document.getElementById('scanner-container').style.display = 'none';

                    // Send the barcode to the backend
                    fetch('/scan_and_scrape', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ barcode: barcodeValue })
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Hide the loading overlay
                        document.getElementById('loadingOverlay').style.display = 'none';

                        if (data.error) {
                            alert(data.error);
                        } else {
                            // Loop through the scraped data and add it to the container
                            const container = document.getElementById("productContainer");
                            container.innerHTML = ''; // Clear previous results
                            data.forEach(item => {
                                const block = document.createElement("div");
                                block.className = "product-block";
                                block.innerHTML = `
                                    <div class="product-details">
                                        <div class="product-site"><img src="${item.image_src}" alt="Product Image">  ${item.site}</div>
                                        <div class="product-name">${item.product}</div>
                                        <div class="product-price">${item.price}</div>
                                        <button class="trace-button" onclick="startTracing('${item.url}')">Trace</button>
                                    </div>
                                `;
                                container.appendChild(block);
                            });

                            // After appending the content, scroll to the results section
                            scrollToResults();
                        }
                    })
                    .catch(error => {
                        // Hide the loading overlay in case of error
                        document.getElementById('loadingOverlay').style.display = 'none';
                        console.error('Error:', error);
                    });

                    // Wait for 1 second before scanning the next barcode
                    await new Promise(resolve => setTimeout(resolve, 1000));
                } catch (err) {
                    // Barcode detection might fail initially
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
            }
        } catch (err) {
            console.error("Error initializing video stream:", err);
        }

    })();
});

// Function to trigger scroll to the results section
function scrollToResults() {
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        // Scroll smoothly to the results section
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Function to start tracing
function startTracing(url) {
    fetch(`/trace/${encodeURIComponent(url)}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert(data.message);
        } else {
            alert('Failed to start tracing.');
        }
    })
    .catch(error => console.error('Error starting tracing:', error));
}