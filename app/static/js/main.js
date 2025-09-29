/**
 * InvoiceX - Main JavaScript file
 * 
 * Contains common functionality used across the application
 * app/static/js/main.js 
*/

document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja tooltipów Bootstrap
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Automatyczne zamykanie alertów po 5 sekundach
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Obsługa tabel z sortowaniem i wyszukiwaniem (jeśli istnieją)
    setupDataTables();

    // Obsługa potwierdzenia usunięcia
    setupDeleteConfirmation();
});

/**
 * Konfiguracja tabel z sortowaniem i wyszukiwaniem
 */
function setupDataTables() {
    // To jest placeholder - w rzeczywistej implementacji można użyć biblioteki DataTables
    const searchInputs = document.querySelectorAll('.table-search');
    
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function() {
            const searchText = this.value.toLowerCase();
            const tableId = this.getAttribute('data-table');
            const table = document.querySelector('#' + tableId);
            
            if (!table) return;
            
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                let matchFound = false;
                const cells = row.querySelectorAll('td');
                
                cells.forEach(cell => {
                    if (cell.textContent.toLowerCase().includes(searchText)) {
                        matchFound = true;
                    }
                });
                
                if (matchFound) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
}

/**
 * Konfiguracja potwierdzeń usunięcia
 */
function setupDeleteConfirmation() {
    document.querySelectorAll('.delete-confirm').forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Czy na pewno chcesz usunąć ten element? Tej operacji nie można cofnąć.')) {
                e.preventDefault();
                return false;
            }
        });
    });
}