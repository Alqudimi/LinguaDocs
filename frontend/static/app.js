const API_BASE = window.location.origin;

let currentProjectId = null;
let pollInterval = null;

const form = document.getElementById('projectForm');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const downloadSection = document.getElementById('downloadSection');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await startTranslationProcess();
});

async function startTranslationProcess() {
    const docUrl = document.getElementById('docUrl').value;
    const sourceType = document.getElementById('sourceType').value;
    const projectName = document.getElementById('projectName').value;
    const sourceLang = document.getElementById('sourceLang').value;
    const targetLang = document.getElementById('targetLang').value;
    const createPackage = document.getElementById('createPackage').checked;

    document.getElementById('startBtn').disabled = true;
    document.getElementById('startBtn').textContent = 'Processing...';
    
    progressSection.classList.remove('hidden');
    progressSection.classList.add('fade-in');
    
    resultsSection.classList.add('hidden');

    try {
        updateStatus('Fetching documentation...', 0);
        updateStepStatus('fetchStatus', 'loading');

        const fetchResponse = await fetch(`${API_BASE}/api/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: docUrl,
                source_type: sourceType,
                max_pages: 50
            })
        });

        const fetchData = await fetchResponse.json();
        
        if (fetchData.status !== 'success') {
            throw new Error('Failed to fetch documentation');
        }

        currentProjectId = fetchData.project_id;
        updateStepStatus('fetchStatus', 'success');
        
        updateStatus('Parsing content...', 33);
        updateStepStatus('parseStatus', 'loading');

        const parseResponse = await fetch(`${API_BASE}/api/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId
            })
        });

        const parseData = await parseResponse.json();
        
        if (parseData.status !== 'success') {
            throw new Error('Failed to parse documentation');
        }

        updateStepStatus('parseStatus', 'success');
        
        updateStatus('Translating text...', 50);
        updateStepStatus('translateStatus', 'loading');

        const translateResponse = await fetch(`${API_BASE}/api/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                source_lang: sourceLang,
                target_lang: targetLang
            })
        });

        const translateData = await translateResponse.json();
        
        if (translateData.status !== 'success') {
            throw new Error('Failed to translate documentation');
        }

        updateStepStatus('translateStatus', 'success');
        
        updateStatus('Building static site...', 80);
        updateStepStatus('buildStatus', 'loading');

        const buildResponse = await fetch(`${API_BASE}/api/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                project_name: projectName,
                create_package: createPackage
            })
        });

        const buildData = await buildResponse.json();
        
        if (buildData.status !== 'success') {
            throw new Error('Failed to build site');
        }

        updateStepStatus('buildStatus', 'success');
        updateStatus('Complete!', 100);

        showResults(buildData, targetLang);

    } catch (error) {
        console.error('Error:', error);
        updateStatus(`Error: ${error.message}`, 0);
        updateStepStatus('fetchStatus', 'error');
        updateStepStatus('parseStatus', 'error');
        updateStepStatus('translateStatus', 'error');
        updateStepStatus('buildStatus', 'error');
    } finally {
        document.getElementById('startBtn').disabled = false;
        document.getElementById('startBtn').textContent = '🚀 Start Translation Process';
    }
}

function updateStatus(message, progress) {
    document.getElementById('statusText').textContent = message;
    document.getElementById('progressPercent').textContent = `${progress}%`;
    document.getElementById('progressBar').style.width = `${progress}%`;
}

function updateStepStatus(elementId, status) {
    const element = document.getElementById(elementId);
    if (status === 'loading') {
        element.textContent = '⏳';
        element.classList.add('pulse');
    } else if (status === 'success') {
        element.textContent = '✅';
        element.classList.remove('pulse');
    } else if (status === 'error') {
        element.textContent = '❌';
        element.classList.remove('pulse');
    }
}

function showResults(buildData, targetLang) {
    resultsSection.classList.remove('hidden');
    
    const buildResult = buildData.build_result;
    const packageResult = buildData.package_result;
    
    let detailsHTML = `
        <p class="text-gray-700">
            <strong>Project:</strong> ${buildResult.project_name}<br>
            <strong>Language:</strong> ${targetLang.toUpperCase()}<br>
            <strong>Pages Generated:</strong> ${buildResult.total_pages}<br>
            <strong>Output Directory:</strong> ${buildResult.site_dir}
        </p>
    `;
    
    if (packageResult && packageResult.status === 'success') {
        detailsHTML += `
            <p class="text-gray-700 mt-2">
                <strong>Package:</strong> ${packageResult.zip_name}<br>
                <strong>Size:</strong> ${packageResult.size_mb} MB
            </p>
        `;
        
        downloadSection.classList.remove('hidden');
        document.getElementById('downloadBtn').onclick = () => {
            window.location.href = `${API_BASE}/api/download/${packageResult.zip_name}`;
        };
    }
    
    document.getElementById('resultDetails').innerHTML = detailsHTML;
}

document.getElementById('sourceType').addEventListener('change', (e) => {
    const urlInput = document.getElementById('docUrl');
    if (e.target.value === 'github') {
        urlInput.placeholder = 'https://github.com/user/repo';
    } else {
        urlInput.placeholder = 'https://docs.example.com';
    }
});
