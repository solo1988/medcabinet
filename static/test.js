const statusEl = document.getElementById('status');
const medInfoCard = document.getElementById('medicineInfo');
const medName = document.getElementById('medName');
const medGTIN = document.getElementById('medGTIN');
const medSerial = document.getElementById('medSerial');
const medExp = document.getElementById('medExp');
const medManufacturer = document.getElementById('medManufacturer');
const medStatus = document.getElementById('medStatus');
const addBtn = document.getElementById('addBtn');
const rescanBtn = document.getElementById('rescanBtn');

let html5QrCode = null;
let currentMedicine = null;
let scanning = false;

function setStatus(text, type = 'scanning') {
    statusEl.textContent = text;
    statusEl.className = `alert text-center status-${type}`;
    statusEl.classList.remove('d-none');
}

async function startScanner() {
    if (html5QrCode && html5QrCode.isScanning) {
        try {
            await html5QrCode.stop();
        } catch (e) {}
    }

    if (!html5QrCode) {
        html5QrCode = new Html5Qrcode("reader");
    }

    scanning = true;
    currentMedicine = null;
    medInfoCard.classList.add('d-none');
    setStatus('Запускаем камеру...', 'scanning');

    const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        formatsToSupport: [Html5QrcodeSupportedFormats.DATA_MATRIX]
    };

    try {
        // Пробуем заднюю камеру
        await html5QrCode.start(
            { facingMode: "environment" },
            config,
            onScanSuccess,
            onScanFailure
        );
        setStatus('Ищем DataMatrix...', 'scanning');
    } catch (err) {
        console.warn("Environment camera failed, trying any camera", err);
        try {
            // Если не получилось — любую доступную
            const cameras = await Html5Qrcode.getCameras();
            if (cameras && cameras.length > 0) {
                await html5QrCode.start(
                    cameras[cameras.length - 1].id, // обычно задняя
                    config,
                    onScanSuccess,
                    onScanFailure
                );
                setStatus('Ищем DataMatrix...', 'scanning');
            } else {
                throw new Error("Камеры не найдены");
            }
        } catch (err2) {
            setStatus('Не удалось запустить камеру. Нажмите кнопку ниже и разрешите доступ.', 'error');
            showStartButton();
        }
    }
}

function showStartButton() {
    let btn = document.getElementById('manualStartBtn');
    if (!btn) {
        btn = document.createElement('button');
        btn.id = 'manualStartBtn';
        btn.className = 'btn btn-primary w-100 mb-3';
        btn.textContent = '📷 Запустить камеру';
        btn.onclick = () => {
            btn.remove();
            startScanner();
        };
        statusEl.after(btn);
    }
}

function onScanSuccess(decodedText, decodedResult) {
    if (!scanning) return;
    scanning = false;

    setStatus('Код захвачен, отправляем на проверку...', 'sending');

    html5QrCode.stop().then(() => {
        checkCode(decodedText);
    }).catch(() => {
        checkCode(decodedText);
    });
}

function onScanFailure(error) {
    // Игнорируем — нормально, пока код не в кадре
}

async function checkCode(code) {
    try {
        const res = await fetch('/check-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();

        if (data.success && data.medicine) {
            currentMedicine = data.medicine;
            showMedicine(data.medicine);
            setStatus('Код распознан и проверен', 'found');
        } else {
            setStatus('Ошибка: ' + (data.error || 'неизвестная'), 'error');
            setTimeout(startScanner, 2500);
        }
    } catch (err) {
        setStatus('Ошибка сети: ' + err.message, 'error');
        setTimeout(startScanner, 2500);
    }
}

function showMedicine(med) {
    medName.textContent = med.name || '—';
    medGTIN.textContent = med.gtin || '—';
    medSerial.textContent = med.serial_number || '—';
    medExp.textContent = med.expiration_date || '—';
    medManufacturer.textContent = med.manufacturer || '—';
    medStatus.textContent = med.status || '—';
    medInfoCard.classList.remove('d-none');
}

addBtn.addEventListener('click', async () => {
    if (!currentMedicine) return;
    if (!confirm(`Добавить "${currentMedicine.name}" в базу?`)) return;

    try {
        const res = await fetch('/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: currentMedicine.code || '',
                name: currentMedicine.name || '',
                gtin: currentMedicine.gtin || '',
                serial_number: currentMedicine.serial_number || '',
                expiration_date: currentMedicine.expiration_date || '',
                manufacturer: currentMedicine.manufacturer || '',
                symptoms: currentMedicine.symptoms || []
            })
        });
        const result = await res.json();
        if (result.status === 'ok') {
            setStatus('Лекарство добавлено', 'found');
            setTimeout(() => window.location.href = '/', 1200);
        } else {
            setStatus('Не удалось добавить', 'error');
        }
    } catch (err) {
        setStatus('Ошибка: ' + err.message, 'error');
    }
});

rescanBtn.addEventListener('click', startScanner);

document.getElementById('btnBack').onclick = () => window.history.back();
document.getElementById('btnHome').onclick = () => window.location.href = '/';

// Пытаемся запустить сразу, если не получится — появится кнопка
startScanner();
