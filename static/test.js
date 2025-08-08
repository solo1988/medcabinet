const video = document.getElementById('video');
const cameraSelect = document.getElementById('cameraSelect');
const resultBox = document.getElementById('resultBox');
const medInfoCard = document.getElementById('medicineInfo');
const medName = document.getElementById('medName');
const medGTIN = document.getElementById('medGTIN');
const medSerial = document.getElementById('medSerial');
const medExp = document.getElementById('medExp');
const medManufacturer = document.getElementById('medManufacturer');
const addBtn = document.getElementById('addBtn');

let stream;
let currentMedicine = null;

async function getCameras() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');
    cameraSelect.innerHTML = '';
    videoDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label || `Камера ${index + 1}`;
        cameraSelect.appendChild(option);
    });

    if (videoDevices.length > 0) {
        cameraSelect.value = videoDevices[videoDevices.length - 1].deviceId; // выбрать последнюю
        await startCamera(cameraSelect.value);
    }
}

async function startCamera(deviceId) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    stream = await navigator.mediaDevices.getUserMedia({
        video: {
            deviceId: deviceId ? {exact: deviceId} : undefined
        },
        audio: false
    });

    video.srcObject = stream;
}

cameraSelect.addEventListener('change', () => {
    const selectedId = cameraSelect.value;
    startCamera(selectedId);
});

async function scanAndSend() {
    if (!stream || video.readyState < 2) {
        alert('Видео ещё не готово, подождите...');
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    resultBox.className = 'alert alert-info';
    resultBox.textContent = '📤 Отправка изображения...';
    resultBox.classList.remove('d-none');
    medInfoCard.classList.add('d-none');

    canvas.toBlob(async (blob) => {
        if (!blob) {
            resultBox.className = 'alert alert-danger';
            resultBox.textContent = '❌ Не удалось создать изображение';
            return;
        }

        const formData = new FormData();
        formData.append('image', blob, 'snapshot.jpg');

        try {
            const res = await fetch('/scan-upload', {
                method: 'POST',
                body: formData
            });
            const raw = await res.text();
            console.log("Ответ от сервера:", raw);

            const data = JSON.parse(raw);

            if (data.success && data.medicine) {
                const med = data.medicine;
                currentMedicine = med;

                medName.textContent = med.name || '';
                medGTIN.textContent = med.gtin || '';
                medSerial.textContent = med.serial_number || '';
                medExp.textContent = med.expiration_date || '';
                medManufacturer.textContent = med.manufacturer || '';

                // Проверяем в базе по serial_number
                if (med.serial_number) {
                    const findRes = await fetch(`/find_by_serial/${encodeURIComponent(med.serial_number)}`);
                    const findData = await findRes.json();

                    if (findData.found) {
                        // Есть препарат — спрашиваем удалить
                        const gtinRes = await fetch(`/count_by_gtin/${encodeURIComponent(med.gtin)}`);
                        const gtinData = await gtinRes.json();

                        if (gtinData.count === 1) {
                            if (confirm(`Препарат "${findData.medicine.name}" с таким серийным номером единственный в базе. Хотите переместить его в архив?`)) {
                                // Перемещаем в архив
                                const archiveRes = await fetch(`/archive/${findData.medicine.id}`, {method: 'POST'});
                                if (archiveRes.ok) {
                                    alert('Препарат перемещён в архив.');
                                    window.location.href = '/';
                                } else {
                                    alert('Ошибка при архивировании.');
                                }
                            } else {
                                alert('Препарат в базе, переход на главную страницу.');
                                window.location.href = '/';
                            }
                        } else {
                            // более одного — удаляем
                            if (confirm(`Препарат "${findData.medicine.name}" с таким серийным номером найден несколько раз. Хотите удалить его?`)) {
                                const delRes = await fetch(`/delete/${findData.medicine.id}`, {method: 'DELETE'});
                                if (delRes.ok) {
                                    alert('Препарат удалён.');
                                    window.location.href = '/';
                                } else {
                                    alert('Ошибка при удалении.');
                                }
                            } else {
                                alert('Препарат в базе, переход на главную страницу.');
                                window.location.href = '/';
                            }
                        }
                        return; // прерываем дальнейшее добавление
                    }
                }

                // Если препарата нет — показываем инфо и кнопку "Добавить"
                resultBox.className = 'alert alert-success';
                resultBox.textContent = '✅ Код распознан, лекарство найдено';
                medInfoCard.classList.remove('d-none');
            } else {
                currentMedicine = null;
                resultBox.className = 'alert alert-warning';
                resultBox.textContent = '⚠️ Не удалось получить данные лекарства: ' + (data.error || '');
            }
        } catch (err) {
            currentMedicine = null;
            resultBox.className = 'alert alert-danger';
            resultBox.textContent = '❌ Ошибка при отправке: ' + err.message;
        }
    }, 'image/jpeg', 0.95);
}

document.getElementById('scanBtn').addEventListener('click', scanAndSend);

addBtn.addEventListener('click', async () => {
    if (!currentMedicine) return;

    if (!confirm(`Добавить препарат "${currentMedicine.name}" в базу?`)) {
        return;
    }

    try {
        const res = await fetch('/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
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
            resultBox.className = 'alert alert-success';
            resultBox.textContent = '✅ Лекарство добавлено в базу';
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            resultBox.className = 'alert alert-danger';
            resultBox.textContent = '❌ Не удалось добавить: ' + JSON.stringify(result);
        }
    } catch (err) {
        resultBox.className = 'alert alert-danger';
        resultBox.textContent = '❌ Ошибка при добавлении: ' + err.message;
    }
});

// Инициализация
getCameras();

$(document).ready(function () {
    // Обработчики кнопок меню
    $('#btnBack').click(() => window.history.back());
    $('#btnHome').click(() => window.location.href = '/');
});