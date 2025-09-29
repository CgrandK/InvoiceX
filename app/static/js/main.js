/**
 * Dabtly - Main JavaScript file
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
    
    // Obsługa formularza faktury (jeśli istnieje na stronie)
    setupInvoiceForm();
    
    // Obsługa tabel z sortowaniem i wyszukiwaniem (jeśli istnieją)
    setupDataTables();
    
    // Obsługa potwierdzenia usunięcia
    setupDeleteConfirmation();
    
    // Obsługa drukowania faktury
    setupPrintButton();
});

/**
 * Konfiguracja formularza faktury
 */
function setupInvoiceForm() {
    const invoiceForm = document.querySelector('#invoice-form');
    if (!invoiceForm) return;
    
    // Dodaj pozycję faktury
    const addItemButton = document.querySelector('#add-item');
    if (addItemButton) {
        addItemButton.addEventListener('click', function() {
            const itemsContainer = document.querySelector('#invoice-items');
            const itemTemplate = document.querySelector('#item-template');
            const newItem = itemTemplate.content.cloneNode(true);
            
            // Aktualizacja indeksów w nowej pozycji
            const itemCount = document.querySelectorAll('.invoice-item').length;
            const inputs = newItem.querySelectorAll('[name]');
            
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                input.setAttribute('name', name.replace('__index__', itemCount));
                input.setAttribute('id', name.replace('__index__', itemCount));
            });
            
            // Dodaj listener do przycisku usunięcia
            const removeButton = newItem.querySelector('.remove-item-btn');
            removeButton.addEventListener('click', function() {
                this.closest('.invoice-item').remove();
                calculateTotals();
            });
            
            // Dodaj listenery do pól do obliczania sumy
            const quantityInput = newItem.querySelector('[name$="quantity"]');
            const priceInput = newItem.querySelector('[name$="unit_price"]');
            
            [quantityInput, priceInput].forEach(input => {
                input.addEventListener('change', calculateTotals);
            });
            
            // Dodaj nową pozycję do kontenera
            itemsContainer.appendChild(newItem);
            
            // Aktualizuj sumę
            calculateTotals();
        });
    }
    
    // Usuń pozycję faktury
    document.querySelectorAll('.remove-item-btn').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.invoice-item').remove();
            calculateTotals();
        });
    });
    
    // Obliczanie sumy pozycji
    document.querySelectorAll('[name$="quantity"], [name$="unit_price"]').forEach(input => {
        input.addEventListener('change', calculateTotals);
    });
    
    // Obliczanie sumy z podatkiem
    document.querySelector('#tax_rate')?.addEventListener('change', calculateTotals);
    document.querySelector('#discount')?.addEventListener('change', calculateTotals);
    
    // Inicjalne obliczenie sumy
    calculateTotals();
}

/**
 * Oblicza sumę pozycji faktury i aktualizuje podsumowanie
 */
function calculateTotals() {
    const items = document.querySelectorAll('.invoice-item');
    let subtotal = 0;
    
    // Oblicz sumę pozycji
    items.forEach(item => {
        const quantity = parseFloat(item.querySelector('[name$="quantity"]').value) || 0;
        const price = parseFloat(item.querySelector('[name$="unit_price"]').value) || 0;
        const total = quantity * price;
        
        // Aktualizuj pole sumy pozycji (jeśli istnieje)
        const totalField = item.querySelector('.item-total');
        if (totalField) {
            totalField.textContent = total.toFixed(2) + ' zł';
        }
        
        subtotal += total;
    });
    
    // Wyświetl subtotal
    const subtotalField = document.querySelector('#subtotal');
    if (subtotalField) {
        subtotalField.textContent = subtotal.toFixed(2) + ' zł';
    }
    
    // Oblicz podatek
    const taxRateField = document.querySelector('#tax_rate');
    let taxRate = 0;
    
    if (taxRateField) {
        taxRate = parseFloat(taxRateField.value) || 0;
    }
    
    const taxAmount = subtotal * (taxRate / 100);
    const taxAmountField = document.querySelector('#tax_amount');
    
    if (taxAmountField) {
        taxAmountField.textContent = taxAmount.toFixed(2) + ' zł';
    }
    
    // Oblicz rabat
    const discountField = document.querySelector('#discount');
    let discount = 0;
    
    if (discountField) {
        discount = parseFloat(discountField.value) || 0;
    }
    
    // Oblicz sumę końcową
    const total = subtotal + taxAmount - discount;
    const totalField = document.querySelector('#total');
    
    if (totalField) {
        totalField.textContent = total.toFixed(2) + ' zł';
    }
    
    // Jeśli jest dostępne API /calculate-totals, użyj go do walidacji
    const invoiceForm = document.querySelector('#invoice-form');
    if (invoiceForm) {
        const formData = {
            items: [],
            tax_rate: taxRate,
            discount: discount
        };
        
        // Zbierz dane o pozycjach
        items.forEach(item => {
            const quantity = parseFloat(item.querySelector('[name$="quantity"]').value) || 0;
            const price = parseFloat(item.querySelector('[name$="unit_price"]').value) || 0;
            
            formData.items.push({
                quantity: quantity,
                unit_price: price
            });
        });
        
        // Opcjonalnie: wyślij do API w celu walidacji
        // Komentujemy to na razie, aby nie generować błędów podczas rozwoju
        /*
        fetch('/invoice/calculate-totals', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Walidacja sum:', data);
        })
        .catch(error => {
            console.error('Błąd walidacji:', error);
        });
        */
    }
}

/**
 * Pobiera token CSRF z meta tagu
 */
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

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

/**
 * Konfiguracja przycisku drukowania faktury
 */
function setupPrintButton() {
    document.querySelector('#print-invoice')?.addEventListener('click', function() {
        window.print();
    });
}