$(document).ready(function () {
    const table = $('#medicineTable').DataTable({
        language: {url: 'static/ru.json'},
        pageLength: 100,
        lengthChange: false,
        searching: true,
        order: [[1, 'asc']],
        columnDefs: [
            {targets: 'd-none-search', visible: false, searchable: true}
        ]
    });

    const selectedApplicationIds = new Set();

    function applyApplicationFilter() {
        $.fn.dataTable.ext.search = $.fn.dataTable.ext.search.filter(fn => !fn._isAppFilter);
        $.fn.dataTable.ext.search.push(Object.assign(function (settings, data, dataIndex) {
            if (selectedApplicationIds.size === 0)
                return true;
            const rowNode = table.row(dataIndex).node();
            const appIdsRaw = $(rowNode).data('appIds');
            let appIds = [];

            if (typeof appIdsRaw === 'string') {
                appIds = appIdsRaw.split(',').map(id => id.trim());
            } else if (Array.isArray(appIdsRaw)) {
                appIds = appIdsRaw.map(id => String(id).trim());
            } else if (appIdsRaw == null) {
                appIds = [];
            } else {
                appIds = String(appIdsRaw).split(',').map(id => id.trim());
            }

            return appIds.some(id => selectedApplicationIds.has(id));
        }, {
            _isAppFilter: true
        }));
        table.draw();
    }

    // Клик по кнопке применения
    $('.application-filter-btn').on('click', function () {
        const btn = $(this);
        const appId = btn.data('app-id').toString();
        if (selectedApplicationIds.has(appId)) {
            selectedApplicationIds.delete(appId);
            btn.removeClass('active');
        } else {
            selectedApplicationIds.add(appId);
            btn.addClass('active');
        }
        applyApplicationFilter();
    });

    // Очистка фильтра
    $('#clearApplicationsFilter').on('click', function () {
        selectedApplicationIds.clear();
        $('.application-filter-btn').removeClass('active');
        applyApplicationFilter();
    });


    let currentMedicineId = null;
    let selectedApplications = [];

    function fetchMedicine(id) {
        $.getJSON(`/medicine/${id}`, data => {
            currentMedicineId = id;
            selectedApplications = data.applications;
            updateApplicationButtons();
        });
    }

    function updateApplicationButtons() {
        $(".application-btn").each(function () {
            const appName = $(this).data("app-name");
            if (selectedApplications.includes(appName)) {
                $(this).removeClass("btn-outline-secondary").addClass("btn-success");
            } else {
                $(this).removeClass("btn-success").addClass("btn-outline-secondary");
            }
        });
    }

    $(document).on("click", ".application-btn", function () {
        const appId = $(this).data("app-id");
        const appName = $(this).data("app-name");
        const isSelected = selectedApplications.includes(appName);

        const url = `/medicine/${currentMedicineId}/applications/${isSelected ? "remove" : "add"}`;
        $.post(url, isSelected ? {application_name: appName} : {application_id: appId}, () => {
            fetchMedicine(currentMedicineId);
        });
    });

    // Фильтр по статусу
    $.fn.dataTable.ext.search.push(function (settings, data, dataIndex, rowData, counter) {
        const rowNode = table.row(dataIndex).node();
        const medData = $(rowNode).data('med');
        if (!medData) return true;
        if (window.currentStatusFilter === 'active') {
            return medData.status === 'active';
        } else if (window.currentStatusFilter === 'archive') {
            return medData.status === 'archive';
        }
        return true;
    });

    // Устанавливаем начальный фильтр
    window.currentStatusFilter = 'active';
    table.draw();

    // Обработчики кнопок переключения фильтра
    $('#btnShowActive').on('click', function () {
        window.currentStatusFilter = 'active';
        table.draw();

        // Кнопки стили
        $('#btnShowActive').addClass('btn-primary').removeClass('btn-outline-secondary');
        $('#btnShowArchive').removeClass('btn-primary').addClass('btn-outline-secondary');
        updateTableImages()
    });

    $('#btnShowArchive').on('click', function () {
        window.currentStatusFilter = 'archive';
        table.draw();

        $('#btnShowArchive').addClass('btn-primary').removeClass('btn-outline-secondary');
        $('#btnShowActive').removeClass('btn-primary').addClass('btn-outline-secondary');
        updateTableImages()
    });

    // Кастомный поиск
    $('#searchInput').on('input', function () {
        table.search(this.value).draw();
    });

    // Меню
    $('#btnBack').click(() => window.history.back());
    $('#btnHome').click(() => window.location.href = '/');
    $('#btnScan').click(() => window.location.href = '/test');
    $('#btnManageApplications').click(() => window.location.href = '/applications');
    $('#btnSearch').click(() => {
        $('#searchBoxContainer').toggle();
        if ($('#searchBoxContainer').is(':visible')) {
            $('#searchInput').val('').focus();
            $('#bottomMenu').hide();
        } else {
            $('#bottomMenu').show();
            table.search('').draw();
        }
    });

    $(document).on('click', function (e) {
        if ($('#searchBoxContainer').is(':visible') &&
            !$(e.target).closest('#searchBoxContainer, #btnSearch').length) {
            $('#searchBoxContainer').hide();
            $('#bottomMenu').show();
            $('#searchInput').val('');
            table.search('').draw();
        }
    });

    // Создаем модалку один раз и слушаем закрытие
    const medModalEl = document.getElementById('medModal');
    const medModal = new bootstrap.Modal(medModalEl);

    medModalEl.addEventListener('hidden.bs.modal', function () {
        // Убираем залипание
        $('body').removeClass('modal-open');
        $('.modal-backdrop').remove();
    });

    // Функции для работы с источником картинки
    function loadImageSource(gtin, callback) {
        $.getJSON(`/image-source/${gtin}`, function (data) {
            if (data && data.source) {
                callback(data.source);
            } else {
                callback("google");
            }
        }).fail(function () {
            callback("google");
        });
    }

    function saveImageSource(gtin, source, callback) {
        $.ajax({
            url: "/image-source",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({gtin: gtin, source: source}),
            success: function () {
                if (callback) callback();
            }
        });
    }

    function updateImages(gtin, source) {
        const googleSrc = `/images/${gtin}.jpg`;
        const yandexSrc = `/yandex_images/${gtin}.jpg`;
        const newSrc = source === "google" ? googleSrc : yandexSrc;

        $('#modal_img').html("<img class='img-fluid' src='" + newSrc + "' alt='Изображение препарата'>");

        // Обновляем картинку в таблице для данного gtin
        $('#medicineTable tbody tr').each(function () {
            const med = $(this).data('med');
            if (med && med.gtin === gtin) {
                $(this).find('td:first-child img').attr('src', newSrc);
            }
        });

        if (source === "google") {
            $('#btnUseGoogle').addClass('active');
            $('#btnUseYandex').removeClass('active');
        } else {
            $('#btnUseYandex').addClass('active');
            $('#btnUseGoogle').removeClass('active');
        }
    }

    // При загрузке страницы обновляем все картинки в таблице в зависимости от выбора источника
    async function updateTableImages() {
        const promises = [];
        $('#medicineTable tbody tr').each(function () {
            const med = $(this).data('med');
            if (med && med.gtin) {
                const gtin = med.gtin;
                const $row = $(this);
                const p = $.getJSON(`/image-source/${gtin}`).then(data => {
                    let src = `/images/${gtin}.jpg`;
                    if (data && data.source === 'yandex') {
                        src = `/yandex_images/${gtin}.jpg`;
                    }
                    $row.find('td:first-child img').attr('src', src);
                }).fail(() => {
                    $row.find('td:first-child img').attr('src', `/images/${gtin}.jpg`);
                });
                promises.push(p);
            }
        });
        await Promise.all(promises);
    }

    updateTableImages();

    // Открытие модального окна по клику на строку
    $('#medicineTable tbody').on('click', 'tr', function () {
        const med = $(this).data('med');
        if (!med) return;

        currentMedicineId = med.id;
        fetchMedicine(currentMedicineId);

        // Заполняем модалку информацией
        $('#modal-name').text(med.name);
        $('#modal-exp').text(med.expiration_date?.split('T')[0]?.split('-').reverse().join('.') || '');
        $('#modal-serial').text(med.serial_number || '—');
        $('#modal-gtin').text(med.gtin || '—');
        $('#modal-manufacturer').text(med.manufacturer || '—');
        $('#modal-added').text(med.added_at?.split('T')[0]?.split('-').reverse().join('.') || '');
        $('#modal-symptoms').html(
            (med.symptoms || []).map(s =>
                `<span class="badge bg-secondary w-100 d-block mb-1 text-break symptom-badge">${s}</span>`
            ).join('')
        );

        // Устанавливаем data-id кнопке
        $('#modal-delete-btn').data('id', med.id);

        // Считаем сколько препаратов с таким GTIN в таблице
        const sameGtinCount = $('#medicineTable tbody tr').filter(function () {
            const m = $(this).data('med');
            return m && m.gtin === med.gtin;
        }).length;

        // В зависимости от статуса и количества меняем кнопку
        if (sameGtinCount === 1) {
            if (med.status === 'active') {
                // Активный — показываем кнопку "В архив"
                $('#modal-delete-btn')
                    .removeClass('btn-danger btn-success')
                    .addClass('btn-warning')
                    .text('В архив')
                    .off('click')
                    .on('click', function () {
                        if (!confirm('Переместить препарат в архив?')) return;

                        $.ajax({
                            url: `/archive/${med.id}`,
                            method: 'POST',
                            success: function () {
                                location.reload();
                            },
                            error: function (xhr, status, error) {
                                alert('Ошибка при архивировании: ' + error);
                            }
                        });
                    });
            } else if (med.status === 'archive') {
                // Архивный — показываем кнопку "Вернуть из архива"
                $('#modal-delete-btn')
                    .removeClass('btn-danger btn-warning')
                    .addClass('btn-success')
                    .text('Вернуть из архива')
                    .off('click')
                    .on('click', function () {
                        if (!confirm('Вернуть препарат из архива?')) return;

                        $.ajax({
                            url: `/unarchive/${med.id}`,
                            method: 'POST',
                            success: function () {
                                location.reload();
                            },
                            error: function (xhr, status, error) {
                                alert('Ошибка при возврате из архива: ' + error);
                            }
                        });
                    });
            }
        } else {
            // Если препаратов с таким GTIN больше одного — показываем кнопку удаления
            $('#modal-delete-btn')
                .removeClass('btn-warning btn-success')
                .addClass('btn-danger')
                .text('Удалить')
                .off('click')
                .on('click', function () {
                    if (!confirm('Удалить этот препарат?')) return;

                    $.ajax({
                        url: `/delete/${med.id}`,
                        type: 'DELETE',
                        success: function () {
                            location.reload();
                        },
                        error: function (xhr, status, error) {
                            alert('Ошибка при удалении: ' + error);
                        }
                    });
                });
        }

        // Загружаем и показываем изображение по источнику
        loadImageSource(med.gtin, function (source) {
            updateImages(med.gtin, source);
        });

        medModal.show();
    });


    // Обработчики переключения источника изображения
    $('#btnUseGoogle').click(function () {
        const gtin = $('#modal-gtin').text();
        if (!gtin || gtin === '—') return;

        saveImageSource(gtin, 'google', function () {
            updateImages(gtin, 'google');
        });
    });

    $('#btnUseYandex').click(function () {
        const gtin = $('#modal-gtin').text();
        if (!gtin || gtin === '—') return;

        saveImageSource(gtin, 'yandex', function () {
            updateImages(gtin, 'yandex');
        });
    });

    // Удаление препарата
    $('#modal-delete-btn').on('click', function () {
        const medId = $(this).data('id');
        if (!confirm('Удалить этот препарат?')) return;

        $.ajax({
            url: `/delete/${medId}`,
            type: 'DELETE',
            success: function () {
                location.reload();
            },
            error: function (xhr, status, error) {
                alert('Ошибка при удалении: ' + error);
            }
        });
    });
});