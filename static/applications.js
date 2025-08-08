$(function () {
    $('#btnHome').click(() => window.location.href = '/');
    $('#btnScan').click(() => window.location.href = '/test');
    $('#btnManageApplications').click(() => window.location.href = '/applications');
    const modal = new bootstrap.Modal($('#applicationModal')[0]);

    // Загрузка данных
    function loadApplications() {
        $.getJSON('/api/applications', function (data) {
            const tbody = $('#applicationsTable tbody');
            tbody.empty();
            data.forEach(app => {
                tbody.append(`
                        <tr>
                            <td>${app.id}</td>
                            <td>${app.name}</td>
                            <td>
                                <button class="btn btn-sm btn-primary btn-edit" data-id="${app.id}" data-name="${app.name}">Редактировать</button>
                                <button class="btn btn-sm btn-danger btn-delete" data-id="${app.id}">Удалить</button>
                            </td>
                        </tr>
                    `);
            });
        });
    }

    loadApplications();

    // Добавление
    $('#btnAddApplication').click(function () {
        $('#applicationModalLabel').text('Добавить применение');
        $('#applicationId').val('');
        $('#applicationName').val('');
        modal.show();
    });

    // Редактирование
    $('#applicationsTable').on('click', '.btn-edit', function () {
        $('#applicationModalLabel').text('Редактировать применение');
        $('#applicationId').val($(this).data('id'));
        $('#applicationName').val($(this).data('name'));
        modal.show();
    });

    // Удаление
    $('#applicationsTable').on('click', '.btn-delete', function () {
        if (!confirm('Удалить применение?')) return;
        const id = $(this).data('id');
        $.ajax({
            url: `/applications/${id}`,
            type: 'DELETE',
            success: loadApplications,
            error: () => alert('Ошибка при удалении')
        });
    });

    // Сохранение (добавление/редактирование)
    $('#applicationForm').submit(function (e) {
        e.preventDefault();
        const id = $('#applicationId').val();
        const name = $('#applicationName').val().trim();

        if (!name) {
            alert('Название обязательно');
            return;
        }

        if (id) {
            // Редактирование
            $.ajax({
                url: `/applications/${id}`,
                method: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify({name}),
                success: function () {
                    modal.hide();
                    loadApplications();
                },
                error: () => alert('Ошибка при обновлении')
            });
        } else {
            // Добавление
            $.ajax({
                url: '/applications',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({name}),
                success: function () {
                    modal.hide();
                    loadApplications();
                },
                error: () => alert('Ошибка при добавлении')
            });
        }
    });
});