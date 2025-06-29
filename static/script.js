const eventsTableBody = document.getElementById('events-table-body');
const selectAllCheckbox = document.getElementById('select-all-checkbox');
const deleteSelectedBtn = document.getElementById('delete-selected-btn');
const refreshInterval = 5000;

function formatTimestamp(isoString) {
    if (!isoString) return 'N/A';
    try {
        const date = new Date(isoString);
        return date.toLocaleString('vi-VN', {
            year: 'numeric', month: 'numeric', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: false
        });
    } catch (e) {
        console.error("Error formatting timestamp:", isoString, e);
        return isoString;
    }
}

function formatObjectDetails(details) {
    if (!details || !Array.isArray(details) || details.length === 0) {
        return 'N/A';
    }
    
    let detailStr = details.slice(0, 3).map(obj => {
        const trackIdStr = obj.track_id ? `ID: ${obj.track_id} - ` : '';
        return `${trackIdStr}Class: ${obj.class_name || 'N/A'} (Conf: ${obj.confidence?.toFixed(2) || 'N/A'})`;
    }).join('<br>'); // Sử dụng <br> cho xuống dòng trong HTML

    if (details.length > 3) {
        detailStr += `<br>(+${details.length - 3} more objects)`;
    }
    return detailStr;
}

function getFilenameFromPath(fullPath) {
    if (!fullPath) return null;
    return fullPath.split(/[\\/]/).pop();
}

function updateBulkActionState() {
    if (!eventsTableBody || !deleteSelectedBtn || !selectAllCheckbox) return;

    const rowCheckboxes = eventsTableBody.querySelectorAll('.row-checkbox');
    const selectedCheckboxes = eventsTableBody.querySelectorAll('.row-checkbox:checked');
    const selectedCount = selectedCheckboxes.length;

    deleteSelectedBtn.disabled = selectedCount === 0;
    deleteSelectedBtn.textContent = `Xóa các mục đã chọn (${selectedCount})`;

    if (rowCheckboxes.length > 0 && selectedCount === rowCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else if (selectedCount > 0) {
        // Trạng thái không xác định khi chỉ một vài checkbox được chọn
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    }

    rowCheckboxes.forEach(checkbox => {
        checkbox.closest('tr')?.classList.toggle('selected', checkbox.checked);
    });
}

function getSelectedEventIds() {
    if (!eventsTableBody) return [];
    return Array.from(eventsTableBody.querySelectorAll('.row-checkbox:checked'))
        .map(cb => parseInt(cb.value, 10))
        .filter(id => !isNaN(id));
}

async function fetchAndDisplayEvents() {
    if (!eventsTableBody) return;

    try {
        const response = await fetch('/api/events?limit=50');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const events = data.events || [];

        eventsTableBody.innerHTML = '';

        if (events.length === 0) {
            eventsTableBody.innerHTML = '<tr><td colspan="7">Không có sự kiện nào được ghi nhận.</td></tr>';
            updateBulkActionState();
            return;
        }

        const fragment = document.createDocumentFragment();
        events.forEach(event => {
            const row = document.createElement('tr');
            row.setAttribute('data-event-id', event.id);

            let snapshotContent = 'Không có';
            if (event.snapshot_path) {
                const filename = getFilenameFromPath(event.snapshot_path);
                if (filename) {
                    snapshotContent = `<img src="/api/snapshots/${filename}" alt="Snapshot" class="snapshot" style="cursor: pointer;" onclick="window.open(this.src, '_blank');" onerror="this.parentElement.innerHTML='Lỗi ảnh';">`;
                } else {
                    snapshotContent = 'Lỗi đường dẫn';
                }
            }
            
            let objectDetailsContent = 'N/A';
            if (event.event_type === 'object_detected' && event.object_details) {
                objectDetailsContent = formatObjectDetails(event.object_details);
            }

            row.innerHTML = `
                <td><input type="checkbox" class="row-checkbox" value="${event.id}"></td>
                <td>${formatTimestamp(event.timestamp)}</td>
                <td>${event.camera_id || 'N/A'}</td>
                <td>${event.event_type || 'N/A'} ${event.triggering_class ? `(${event.triggering_class})` : ''}</td>
                <td class="details">${objectDetailsContent}</td>
                <td>${snapshotContent}</td>
                <td><button class="delete-btn" data-event-id="${event.id}">Xóa</button></td>
            `;
            fragment.appendChild(row);
        });

        eventsTableBody.appendChild(fragment);
        updateBulkActionState();

    } catch (error) {
        console.error('Error fetching or displaying events:', error);
        if (eventsTableBody) {
             eventsTableBody.innerHTML = '<tr><td colspan="7">Lỗi khi tải dữ liệu sự kiện.</td></tr>';
        }
        updateBulkActionState();
    }
}

async function deleteEvent(eventId) {
    try {
        const response = await fetch(`/api/events/${eventId}`, { method: 'DELETE' });
        if (response.ok || response.status === 204) {
            eventsTableBody.querySelector(`tr[data-event-id="${eventId}"]`)?.remove();
            updateBulkActionState();
        } else {
            const errorData = await response.json().catch(() => ({}));
            const detail = errorData.detail || `HTTP error ${response.status}`;
            alert(`Lỗi khi xóa sự kiện ${eventId}: ${detail}`);
        }
    } catch (error) {
        console.error('Network or other error deleting event:', error);
        alert('Lỗi mạng khi cố gắng xóa sự kiện.');
    }
}

async function deleteSelectedEvents() {
    const selectedIds = getSelectedEventIds();
    if (selectedIds.length === 0) {
        alert("Vui lòng chọn ít nhất một sự kiện để xóa.");
        return;
    }

    if (!confirm(`Bạn có chắc chắn muốn xóa ${selectedIds.length} sự kiện đã chọn không?`)) {
        return;
    }

    try {
        const response = await fetch('/api/events/delete-bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_ids: selectedIds })
        });

        if (response.ok) {
            const result = await response.json();
            alert(result.message || `${selectedIds.length} sự kiện đã được xóa thành công.`);
            selectedIds.forEach(id => {
                eventsTableBody.querySelector(`tr[data-event-id="${id}"]`)?.remove();
            });
        } else {
             let errorDetail = `HTTP error ${response.status}`;
             try {
                 const errorData = await response.json();
                 errorDetail = errorData.detail || errorDetail;
             } catch (e) { /* Ignore if response is not JSON */ }
             alert(`Lỗi khi xóa hàng loạt: ${errorDetail}`);
        }
    } catch (error) {
         console.error('Network or other error during bulk delete:', error);
         alert('Lỗi mạng khi cố gắng xóa hàng loạt sự kiện.');
    } finally {
         if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
         }
         updateBulkActionState();
    }
}


function setupEventListeners() {
    if (eventsTableBody) {
        eventsTableBody.addEventListener('click', e => {
            if (e.target?.classList.contains('delete-btn')) {
                const eventId = e.target.getAttribute('data-event-id');
                if (eventId && confirm(`Bạn có chắc chắn muốn xóa sự kiện ID ${eventId} không?`)) {
                    deleteEvent(eventId);
                }
            }
        });

        eventsTableBody.addEventListener('change', e => {
            if (e.target?.classList.contains('row-checkbox')) {
                updateBulkActionState();
            }
        });
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', () => {
            const isChecked = selectAllCheckbox.checked;
            eventsTableBody?.querySelectorAll('.row-checkbox').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateBulkActionState();
        });
    }

    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', deleteSelectedEvents);
    }
}

function initializeApp() {
    if (!eventsTableBody || !selectAllCheckbox || !deleteSelectedBtn) {
        console.error("Critical UI elements not found. App initialization failed.");
        if (eventsTableBody) {
            eventsTableBody.innerHTML = '<tr><td colspan="7">Lỗi khởi tạo giao diện.</td></tr>';
        }
        return;
    }

    fetchAndDisplayEvents();
    updateBulkActionState();
    setupEventListeners();

    setInterval(() => {
        if (document.getElementById('events-table-body')) {
            fetchAndDisplayEvents();
        }
    }, refreshInterval);

    console.log(`UI initialized. Refreshing every ${refreshInterval / 1000} seconds.`);
}

document.addEventListener('DOMContentLoaded', initializeApp);