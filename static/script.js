let currentBlob = null;
let currentFilename = "code";

// ---------- Navigation ----------
function showStep(id) {
    document.querySelectorAll(".step").forEach(s => s.classList.add("hidden"));
    document.getElementById(id).classList.remove("hidden");
}

function goHome() {
    currentBlob = null;
    currentFilename = "code";
    document.getElementById("preview").innerHTML = "";
    document.getElementById("qr-link").value = "";
    document.getElementById("bc-text").value = "";
    document.getElementById("bc-text").disabled = false;
    document.querySelector('input[name="bc-mode"][value="manual"]').checked = true;
    showStep("step1");
}

function chooseType(type) {
    if (type === "qr") showStep("step-qr");
    else showStep("step-barcode");
}

// ---------- QR ----------
async function generateQR() {
    const link = document.getElementById("qr-link").value.trim();
    if (!link) {
        alert("Link zaroori hai. Bina link QR nahi banega.");
        return;
    }

    const output_format = document.getElementById("qr-format").value;

    try {
        const res = await fetch("/api/qrcode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link, output_format }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || "QR generate nahi ho saka.");
            return;
        }

        await showResult(res, output_format, "qrcode");
    } catch (e) {
        alert("Network error: " + e.message);
    }
}

// ---------- Barcode ----------
async function generateBarcode() {
    const barcode_format = document.getElementById("bc-format").value;
    const mode = document.querySelector('input[name="bc-mode"]:checked').value;
    const text = document.getElementById("bc-text").value.trim();
    const output_format = document.getElementById("bc-out-format").value;

    if (mode === "manual" && !text) {
        alert("Code likhein ya 'Auto-generate' select karein.");
        return;
    }

    try {
        const res = await fetch("/api/barcode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text,
                auto: mode === "auto",
                barcode_format,
                output_format,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || "Barcode generate nahi ho saka.");
            return;
        }

        await showResult(res, output_format, `barcode-${barcode_format}`);
    } catch (e) {
        alert("Network error: " + e.message);
    }
}

// ---------- Result ----------
async function showResult(res, format, name) {
    const blob = await res.blob();
    currentBlob = blob;
    currentFilename = `${name}.${format}`;

    const url = URL.createObjectURL(blob);
    const preview = document.getElementById("preview");
    preview.innerHTML = `<img src="${url}" alt="generated code">`;

    showStep("step-result");
}

function downloadImage() {
    if (!currentBlob) return;
    const url = URL.createObjectURL(currentBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = currentFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- Toggle manual input ----------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('input[name="bc-mode"]').forEach(r => {
        r.addEventListener("change", (e) => {
            const input = document.getElementById("bc-text");
            if (e.target.value === "auto") {
                input.disabled = true;
                input.value = "";
                input.placeholder = "(auto-generate on)";
            } else {
                input.disabled = false;
                input.placeholder = "Code yahan likhein";
            }
        });
    });
});