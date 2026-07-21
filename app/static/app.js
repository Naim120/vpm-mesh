// App State
let activeTab = "dashboard";
let activeFile = "not_uploaded.txt";
let lastLogCount = 0;
let statusInterval = null;

// DOM Elements
const navItems = document.querySelectorAll(".nav-item");
const tabContents = document.querySelectorAll(".tab-content");
const pageTitle = document.getElementById("page-title");
const pageSubtitle = document.getElementById("page-subtitle");

const serverStatusDot = document.getElementById("server-status-dot");
const serverStatusText = document.getElementById("server-status-text");
const quickProgress = document.getElementById("quick-progress");

// Dashboard Elements
const startNumberInput = document.getElementById("start-number");
const endNumberInput = document.getElementById("end-number");
const btnStart = document.getElementById("btn-start");
const btnResume = document.getElementById("btn-resume");
const btnStop = document.getElementById("btn-stop");
const currentRangeBadge = document.getElementById("current-range-badge");

const progressBarFill = document.getElementById("progress-bar-fill");
const progressPercent = document.getElementById("progress-percent");
const progressNums = document.getElementById("progress-nums");
const progressEta = document.getElementById("progress-eta");

const statTotalRequests = document.getElementById("stat-total-requests");
const statSuccessCount = document.getElementById("stat-success-count");
const statFilesUploaded = document.getElementById("stat-files-uploaded");
const statNotUploaded = document.getElementById("stat-not-uploaded");
const statFailedCount = document.getElementById("stat-failed-count");
const statNoDataCount = document.getElementById("stat-no-data-count");

const terminalOutput = document.getElementById("terminal-output");
const terminalAutoscroll = document.getElementById("terminal-autoscroll");
const btnClearTerminal = document.getElementById("btn-clear-terminal");

// Log Files Elements
const fileTabs = document.querySelectorAll(".file-tab");
const currentViewingFile = document.getElementById("current-viewing-file");
const fileContentViewer = document.getElementById("file-content-viewer");
const btnRefreshFile = document.getElementById("btn-refresh-file");
const btnClearFile = document.getElementById("btn-clear-file");
const btnDownloadFile = document.getElementById("btn-download-file");

const countNotUploaded = document.getElementById("count-not_uploaded");
const countFailed = document.getElementById("count-failed");
const countNoData = document.getElementById("count-no_data");

// Settings Elements
const settingsForm = document.getElementById("settings-form");
const settingProxyUrl = document.getElementById("setting-proxy-url");
const settingMinDelay = document.getElementById("setting-min-delay");
const settingMaxDelay = document.getElementById("setting-max-delay");
const settingGDriveFolderId = document.getElementById("setting-gdrive-folder-id");
const settingGDriveJson = document.getElementById("setting-gdrive-json");
const btnTestDrive = document.getElementById("btn-test-drive");
const testConnectionStatus = document.getElementById("test-connection-status");

// Toast Notification
const toast = document.getElementById("toast");

/* Toast Helpers */
function showToast(message, isError = false) {
    toast.textContent = message;
    toast.style.borderLeftColor = isError ? "var(--danger)" : "var(--primary)";
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}

/* Tab Switching */
navItems.forEach(item => {
    item.addEventListener("click", () => {
        const tab = item.getAttribute("data-tab");
        switchTab(tab);
    });
});

function switchTab(tab) {
    activeTab = tab;
    
    // Update menu buttons
    navItems.forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-tab") === tab);
    });
    
    // Update contents
    tabContents.forEach(content => {
        content.classList.toggle("active", content.getAttribute("id") === `tab-${tab}`);
    });
    
    // Update headers
    if (tab === "dashboard") {
        pageTitle.textContent = "Dashboard";
        pageSubtitle.textContent = "Control and monitor your background scraper";
    } else if (tab === "files") {
        pageTitle.textContent = "Log Files";
        pageSubtitle.textContent = "View and download scraping result logs";
        loadFileContent(activeFile);
        updateFileCounters();
    } else if (tab === "settings") {
        pageTitle.textContent = "Settings";
        pageSubtitle.textContent = "Configure scraper parameters and API credentials";
    }
}

function openSessionModal(sessionData, onResume, onStartFresh) {
    const modal = document.getElementById("session-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalDesc = document.getElementById("modal-desc");
    const modalBadge = document.getElementById("modal-status-badge");
    const modalActions = document.getElementById("modal-actions");

    modal.classList.remove("hidden");
    modalActions.innerHTML = "";

    const isCompleted = sessionData.status === "completed" || sessionData.status === "complete";

    if (isCompleted) {
        modalTitle.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--success)"></i> Session Already Completed`;
        modalDesc.innerHTML = `Session <strong>${sessionData.session_name}</strong> already exists and is <strong>COMPLETED</strong> up to number <strong>${sessionData.end_num}</strong>.`;
        modalBadge.className = "modal-badge completed";
        modalBadge.textContent = "STATUS: COMPLETED";

        // Option 1: Start Fresh
        const btnFresh = document.createElement("button");
        btnFresh.className = "btn btn-primary";
        btnFresh.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Start Fresh from ${sessionData.start_num}`;
        btnFresh.onclick = () => {
            modal.classList.add("hidden");
            onStartFresh();
        };
        modalActions.appendChild(btnFresh);

        // Option 2: Cancel
        const btnCancel = document.createElement("button");
        btnCancel.className = "btn btn-secondary";
        btnCancel.innerHTML = `<i class="fa-solid fa-xmark"></i> Cancel`;
        btnCancel.onclick = () => modal.classList.add("hidden");
        modalActions.appendChild(btnCancel);
    } else {
        modalTitle.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:var(--warning)"></i> Existing Session Found`;
        modalDesc.innerHTML = `Session <strong>${sessionData.session_name}</strong> already exists and paused at document <strong>#${sessionData.current_num}</strong> of <strong>${sessionData.end_num}</strong>.`;
        modalBadge.className = "modal-badge not_complete";
        modalBadge.textContent = "STATUS: NOT COMPLETED";

        // Option 1: Resume
        const btnResume = document.createElement("button");
        btnResume.className = "btn btn-primary";
        btnResume.innerHTML = `<i class="fa-solid fa-play"></i> Resume from Document #${sessionData.current_num}`;
        btnResume.onclick = () => {
            modal.classList.add("hidden");
            onResume();
        };
        modalActions.appendChild(btnResume);

        // Option 2: Start Fresh
        const btnFresh = document.createElement("button");
        btnFresh.className = "btn btn-secondary";
        btnFresh.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Start Fresh from ${sessionData.start_num}`;
        btnFresh.onclick = () => {
            modal.classList.add("hidden");
            onStartFresh();
        };
        modalActions.appendChild(btnFresh);

        // Option 3: Cancel
        const btnCancel = document.createElement("button");
        btnCancel.className = "btn btn-secondary";
        btnCancel.style.opacity = "0.7";
        btnCancel.innerHTML = `<i class="fa-solid fa-xmark"></i> Cancel`;
        btnCancel.onclick = () => modal.classList.add("hidden");
        modalActions.appendChild(btnCancel);
    }
}

/* Scraper Control APIs */
btnStart.addEventListener("click", async () => {
    const startNum = parseInt(startNumberInput.value);
    const endNum = parseInt(endNumberInput.value);
    
    if (isNaN(startNum) || isNaN(endNum)) {
        showToast("Please enter valid start and end numbers.", true);
        return;
    }
    
    if (startNum > endNum) {
        showToast("Start number cannot be greater than end number.", true);
        return;
    }

    try {
        const checkRes = await fetch("/api/check-session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start_num: startNum, end_num: endNum })
        });
        const checkData = await checkRes.json();

        const launchScraper = async (mode) => {
            try {
                const res = await fetch("/api/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ start_num: startNum, end_num: endNum, mode: mode })
                });
                
                if (res.ok) {
                    showToast(`Scraper started (${mode === 'resume' ? 'Resumed' : 'Fresh Start'}).`);
                    terminalOutput.innerHTML = `<div class="terminal-line system-msg">[System] Scraper started (${mode}).</div>`;
                    lastLogCount = 0;
                    pollStatus();
                } else {
                    const err = await res.json();
                    showToast(`Failed to start: ${err.detail}`, true);
                }
            } catch (e) {
                showToast(`Error: ${e.message}`, true);
            }
        };

        if (checkData.exists) {
            openSessionModal(
                checkData,
                () => launchScraper("resume"),
                () => launchScraper("start_fresh")
            );
        } else {
            launchScraper("start_fresh");
        }
    } catch (e) {
        showToast(`Error checking session: ${e.message}`, true);
    }
});

btnResume.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/resume", { method: "POST" });
        if (res.ok) {
            showToast("Scraping worker resumed.");
            pollStatus();
        } else {
            const err = await res.json();
            showToast(`Failed to resume: ${err.detail}`, true);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, true);
    }
});

btnStop.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/stop", { method: "POST" });
        if (res.ok) {
            showToast("Stop request sent to scraper.");
            pollStatus();
        } else {
            const err = await res.json();
            showToast(`Failed to stop: ${err.detail}`, true);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, true);
    }
});

btnClearTerminal.addEventListener("click", () => {
    terminalOutput.innerHTML = '<div class="terminal-line system-msg">[System] Console cleared.</div>';
    lastLogCount = 0;
});

/* Settings APIs */
async function saveSettingsHelper() {
    const proxyUrl = settingProxyUrl.value.trim() || null;
    const minDelay = parseInt(settingMinDelay.value);
    const maxDelay = parseInt(settingMaxDelay.value);
    const folderId = settingGDriveFolderId.value.trim();
    const gDriveJsonText = settingGDriveJson.value.trim();
    
    if (minDelay < 1 || maxDelay < 2 || minDelay >= maxDelay) {
        showToast("Invalid delay range. Min delay must be less than max delay.", true);
        return false;
    }
    
    let gDriveJson = null;
    if (gDriveJsonText) {
        try {
            gDriveJson = JSON.parse(gDriveJsonText);
        } catch (err) {
            showToast("Google Credentials JSON is not valid JSON.", true);
            return false;
        }
    }
    
    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                proxy_url: proxyUrl,
                min_delay: minDelay,
                max_delay: maxDelay,
                gdrive_folder_id: folderId,
                gdrive_service_account: gDriveJson
            })
        });
        
        if (res.ok) {
            showToast("Settings saved and updated successfully.");
            pollStatus(); // Refresh config display
            return true;
        } else {
            const err = await res.json();
            showToast(`Failed to save settings: ${err.detail}`, true);
            return false;
        }
    } catch (err) {
        showToast(`Error: ${err.message}`, true);
        return false;
    }
}

settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    await saveSettingsHelper();
});

btnTestDrive.addEventListener("click", async () => {
    testConnectionStatus.textContent = "Saving and testing connection...";
    testConnectionStatus.className = "test-status";
    
    // Automatically submit & save settings first
    const gDriveJsonText = settingGDriveJson.value.trim();
    if (gDriveJsonText !== "" || settingGDriveFolderId.value.trim() !== "") {
        const saved = await saveSettingsHelper();
        if (!saved) {
            testConnectionStatus.textContent = "Failed: Could not save credentials.";
            testConnectionStatus.className = "test-status error";
            return;
        }
    }

    try {
        const res = await fetch("/api/test-drive", { method: "POST" });
        const data = await res.json();
        
        if (data.success) {
            testConnectionStatus.textContent = `Success! Connected to Folder: "${data.folder_name}"`;
            testConnectionStatus.className = "test-status success";
            showToast("Google Drive connection test passed!");
        } else {
            testConnectionStatus.textContent = `Failed: ${data.error}`;
            testConnectionStatus.className = "test-status error";
            showToast("Google Drive connection test failed.", true);
        }
    } catch (err) {
        testConnectionStatus.textContent = `Error: ${err.message}`;
        testConnectionStatus.className = "test-status error";
    }
});

/* Log Files Tab Logic */
fileTabs.forEach(tab => {
    tab.addEventListener("click", () => {
        fileTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        
        activeFile = tab.getAttribute("data-file");
        currentViewingFile.textContent = activeFile;
        loadFileContent(activeFile);
    });
});

async function loadFileContent(filename) {
    fileContentViewer.textContent = "Loading file content...";
    btnDownloadFile.href = `/api/files/${filename}/download`;
    
    try {
        const res = await fetch(`/api/files/${filename}`);
        if (res.ok) {
            const data = await res.json();
            if (data.content.trim() === "") {
                fileContentViewer.textContent = "-- Empty File --";
            } else {
                fileContentViewer.textContent = data.content;
            }
            
            // Update the count description in sidebar tab
            const countEl = document.getElementById(`count-${filename.replace(".", "_")}`);
            if (countEl) {
                countEl.textContent = `${data.lines_count} entries`;
            }
        } else {
            fileContentViewer.textContent = "Error reading log file.";
        }
    } catch (e) {
        fileContentViewer.textContent = `Error: ${e.message}`;
    }
}

async function updateFileCounters() {
    const files = ["not_uploaded.txt", "failed.txt", "no_data.txt"];
    for (const filename of files) {
        try {
            const res = await fetch(`/api/files/${filename}`);
            if (res.ok) {
                const data = await res.json();
                const countEl = document.getElementById(`count-${filename.replace(".", "_")}`);
                if (countEl) {
                    countEl.textContent = `${data.lines_count} entries`;
                }
            }
        } catch (e) {}
    }
}

btnRefreshFile.addEventListener("click", () => {
    loadFileContent(activeFile);
    updateFileCounters();
    showToast("File content reloaded.");
});

btnClearFile.addEventListener("click", async () => {
    if (!confirm(`Are you sure you want to completely clear ${activeFile}?`)) return;
    
    try {
        const res = await fetch(`/api/files/${activeFile}/clear`, { method: "POST" });
        if (res.ok) {
            showToast(`${activeFile} has been cleared.`);
            loadFileContent(activeFile);
            updateFileCounters();
        } else {
            showToast("Failed to clear file.", true);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, true);
    }
});

/* Scraper Status Polling */
async function pollStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();
        
        // Update sidebar status dot & text
        serverStatusDot.className = `status-dot status-${data.status}`;
        
        // Format status string
        let displayStatus = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        if (data.status === "error" && data.error_message) {
            displayStatus += ` (${data.error_message})`;
        }
        serverStatusText.textContent = `Status: ${displayStatus}`;
        
        // Populate range inputs on initial load if empty
        if (!startNumberInput.value && data.start_num) {
            startNumberInput.value = data.start_num;
        }
        if (!endNumberInput.value && data.end_num) {
            endNumberInput.value = data.end_num;
        }
        
        // Disable inputs while running
        startNumberInput.disabled = (data.status === "running");
        endNumberInput.disabled = (data.status === "running");
        
        // Update current range badge
        currentRangeBadge.textContent = `Range: ${data.start_num} to ${data.end_num}`;
        
        // Update stats
        statTotalRequests.textContent = data.stats.total_requests;
        statSuccessCount.textContent = data.stats.success_count;
        statFilesUploaded.textContent = data.stats.files_uploaded;
        statNotUploaded.textContent = data.stats.not_uploaded_count;
        statFailedCount.textContent = data.stats.failed_count;
        statNoDataCount.textContent = data.stats.no_data_count;
        
        // Quick summary in header
        const totalToProcess = data.end_num - data.start_num + 1;
        const processedSoFar = data.status === "completed" ? totalToProcess : Math.max(0, data.current_num - data.start_num);
        quickProgress.textContent = `${processedSoFar}/${totalToProcess} Processed`;
        
        // Enable/Disable buttons based on status
        if (data.status === "running") {
            btnStart.disabled = true;
            btnResume.disabled = true;
            btnStop.disabled = false;
        } else {
            btnStart.disabled = false;
            btnResume.disabled = (data.current_num > data.end_num);
            btnStop.disabled = true;
        }
        
        // Update Progress Bar
        let progressPct = 0;
        if (data.status === "completed") {
            progressPct = 100;
        } else if (totalToProcess > 0) {
            progressPct = Math.min(100, Math.floor((processedSoFar / totalToProcess) * 100));
        }
        
        progressBarFill.style.width = `${progressPct}%`;
        progressPercent.textContent = `${progressPct}%`;
        
        if (data.status === "running") {
            progressNums.textContent = `Processing URL ending in: ${data.current_num}`;
            progressEta.textContent = `Target: ${data.end_num}`;
        } else if (data.status === "completed") {
            progressNums.textContent = "All URL schedules processed successfully.";
            progressEta.textContent = "Finished";
        } else if (data.status === "stopped") {
            progressNums.textContent = `Stopped at: ${data.current_num}`;
            progressEta.textContent = "Paused";
        } else {
            progressNums.textContent = "Awaiting range submission.";
            progressEta.textContent = "Idle";
        }
        
        // Populate settings inputs if they are empty
        if (!settingProxyUrl.value && data.proxy_url) {
            settingProxyUrl.value = data.proxy_url;
        }
        if (settingMinDelay.value == 30 && data.min_delay) {
            settingMinDelay.value = data.min_delay;
        }
        if (settingMaxDelay.value == 60 && data.max_delay) {
            settingMaxDelay.value = data.max_delay;
        }
        if (!settingGDriveFolderId.value && data.gdrive_folder_id) {
            settingGDriveFolderId.value = data.gdrive_folder_id;
        }
        
        // Process Logs
        if (data.logs.length !== lastLogCount) {
            if (data.logs.length < lastLogCount) {
                terminalOutput.innerHTML = "";
                lastLogCount = 0;
            }
            
            for (let i = lastLogCount; i < data.logs.length; i++) {
                const line = data.logs[i];
                const div = document.createElement("div");
                div.className = "terminal-line";
                
                if (line.includes("failed") || line.includes("Failed") || line.includes("error") || line.includes("Error") || line.includes("except")) {
                    div.classList.add("error-msg");
                } else if (line.includes("success") || line.includes("Success") || line.includes("Uploaded") || line.includes("Downloaded")) {
                    div.classList.add("success-msg");
                } else if (line.includes("Started") || line.includes("Resumed") || line.includes("Stop") || line.includes("Finished")) {
                    div.classList.add("system-msg");
                }
                
                div.textContent = line;
                terminalOutput.appendChild(div);
            }
            
            lastLogCount = data.logs.length;
            
            if (terminalAutoscroll.checked) {
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }
        }
        
    } catch (err) {
        console.error("Error polling scraper status:", err);
    }
}

// Initial setup
switchTab("dashboard");
pollStatus();
// Start background status polling
statusInterval = setInterval(pollStatus, 1500);
updateFileCounters();
