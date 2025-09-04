// static/js/sales.js
document.addEventListener('DOMContentLoaded', function() {
    const saleForm = document.getElementById('sale-form');
    if (!saleForm) return;

    // 1. Inicializar Select2 para búsqueda
    $('.select2-busqueda').select2({
        placeholder: "🔍 Seleccione un elemento",
        language: "es",
        width: '100%',
        minimumInputLength: 0,
        allowClear: true,
        theme: 'default'
    });

    // Quita el setTimeout si todo funciona bien sin él:
    (function initSelects(){
        let customerSelect = document.getElementById('customer-select') || document.querySelector('[name="customer_id"]');
        let sellerSelect   = document.getElementById('seller-select')   || document.querySelector('[name="seller_id"]');
        if (customerSelect) { updateCustomerData(customerSelect); $(customerSelect).on('change', () => updateCustomerData(customerSelect)); }
        if (sellerSelect)   { updateSellerData(sellerSelect);   $(sellerSelect).on('change',   () => updateSellerData(sellerSelect)); }
    })();
  

// Seleccionar por defecto el primer vendedor del listado
(function selectDefaultSeller() {
    const sellerSelect =
      document.getElementById('seller-select') ||
      document.querySelector('[name="seller_id"]');
  
    if (!sellerSelect) return;
  
    // Solo si no hay uno seleccionado aún (o es vacío)
    if (!sellerSelect.value) {
      // Busca el primer <option> con value no vacío y no deshabilitado
      const firstReal =
        Array.from(sellerSelect.options).find(o => o.value && !o.disabled);
  
      if (firstReal) {
        // Fija el valor en el <select>
        sellerSelect.value = firstReal.value;
  
        // Refleja en la UI de Select2
        if (window.jQuery) $(sellerSelect).val(firstReal.value).trigger('change');
  
        // Actualiza el hidden del vendedor
        if (typeof updateSellerData === 'function') updateSellerData(sellerSelect);
      }
    }
  })();
  

    // 3. Funciones para manejar items de venta
    function addRowFromProduct(p){
        addRow(p.sku, p.description, 1, p.price, p.tax_rate);
    }
    
    function addRow(sku="", desc="", qty=1, price=0, tax=0){
        const tbody = document.getElementById('items-body');
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input value="${sku}" readonly oninput="sync()" /></td>
            <td><input value="${desc}" readonly oninput="sync()" /></td>            
            <td><input class="right" type="number" value="${price}" readonly oninput="sync()"/></td>            
            <td><input class="right edit" type="number" value="${qty}" oninput="sync()"/></td>    
            <td><input class="right edit" type="number" value="${tax}" oninput="sync()"/></td>
            <td class="right" data-importe>0.00</td>
            <td><button type="button" onclick="this.closest('tr').remove(); sync();">✖</button></td>
        `;
        tbody.appendChild(tr);
        sync();
    }
    
    function sync(){
        let subtotal=0, tax=0, total=0;
        const rows = [...document.querySelectorAll('#items-body tr')];
        rows.forEach(tr=>{
            const [sku, desc, price, qty, taxrate] = [...tr.querySelectorAll('input')].map(i=>i.value);
            const q = parseFloat(qty||0), p = parseFloat(price||0), t = parseFloat(taxrate||0);
            const line = Math.max(0, (q*p) * (1+t));
            tr.querySelector('[data-importe]').textContent = line.toFixed(2);
            subtotal += q*p;
            tax += (q*p)*t;
            total += line;
        });
        const fmt = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById('t-subtotal').textContent = fmt.format(subtotal);
        document.getElementById('t-tax').textContent      = fmt.format(tax);
        document.getElementById('t-total').textContent    = fmt.format(total);
        

        // empaquetar arrays para POST
        const hidden = document.getElementById('hidden-arrays');
        hidden.innerHTML = '';
        rows.forEach(tr=>{
            const [sku, desc, price, qty, taxrate] = [...tr.querySelectorAll('input')].map(i=>i.value);
            ["sku","desc","price","qty","tax"].forEach((k,idx)=>{
                const v = [sku,desc,qty,price,taxrate][idx];
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = k + '[]';
                input.value = v;
                hidden.appendChild(input);
            });
        });
    }

    window.sync = sync;

    // 4. Evento para búsqueda rápida de productos
    document.addEventListener('click', e=>{
        const li = e.target.closest('[data-sku]');
        if(li){ addRowFromProduct(JSON.parse(li.dataset.payload)); }
    });

    // Al final del DOMContentLoaded, añade:
    const form = document.getElementById('sale-form');
    if (form) {
    form.addEventListener('submit', function () {
        // Asegura que los hidden de alumno y vendedor queden seteados
        const customerSelect = document.getElementById('customer-select') || document.querySelector('[name="customer_id"]');
        const sellerSelect   = document.getElementById('seller-select')   || document.querySelector('[name="seller_id"]');

        if (customerSelect) updateCustomerData(customerSelect);
        if (sellerSelect)   updateSellerData(sellerSelect);

        // Recalcula totales y reempaqueta arrays antes de enviar
        // (sync() ya existe dentro de este mismo scope)
        typeof sync === 'function' && sync();

        console.log('✅ Hidden y arrays actualizados en submit');
    });
    }

    // === Vista previa de "Cambio" (no afecta al backend) ===
    function calcChangePreview() {
        const method = (document.getElementById('payment-method')?.value || '').toUpperCase();
        const tendered = parseFloat(document.getElementById('payment-tendered')?.value || '0') || 0;
        // Lee el total mostrado en la UI (quita comas si las hubiera)
        const totalText = document.getElementById('t-total')?.textContent || '0';
        const total = parseFloat(String(totalText).replace(/[^\d.-]/g, '')) || 0;
    
        // Solo mostramos la fila de cambio si tiene sentido (efectivo y hay monto)
        const row = document.getElementById('row-change');
        if (!row) return;
    
        if (method === 'CASH' || method === 'EFECTIVO') {
        const change = Math.max(0, tendered - total);
        document.getElementById('t-change').textContent = change.toFixed(2);
        row.style.display = (tendered > 0) ? '' : 'none';
        } else {
        row.style.display = 'none';
        }
    }
    
    // engancha eventos
    document.getElementById('payment-method')?.addEventListener('change', calcChangePreview);
    document.getElementById('payment-tendered')?.addEventListener('input', calcChangePreview);
    
    // si tienes una función sync() que recalcula totales, refresca vista previa al final
    if (typeof sync === 'function') {
        const _sync = sync;
        window.sync = function() {
        _sync();
        calcChangePreview();
        };
    } else {
        // si aún no expones sync global, al menos calcula una vez al cargar
        calcChangePreview();
    }
  

});

// ============================================================
// FUNCIONES GLOBALES (deben estar FUERA del DOMContentLoaded)
// ============================================================

// Actualizar datos del alumno
function updateCustomerData(selectElement) {
    if (!selectElement || !selectElement.options) {
        console.error('Elemento customer no válido:', selectElement);
        return;
    }
    
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    if (!selectedOption) return;
    
    const customerName = selectedOption.getAttribute('data-name') || '';
    const customerEnrollment = selectedOption.getAttribute('data-enrollment') || '';
    
    // Actualizar campos hidden
    const nameField = document.getElementById('customer-name');
    const enrollmentField = document.getElementById('customer-enrollment');
    
    if (nameField) nameField.value = customerName;
    if (enrollmentField) enrollmentField.value = customerEnrollment;
    
    console.log('Customer hidden fields updated:', customerName, customerEnrollment);
}

// Actualizar datos del vendedor
function updateSellerData(selectElement) {
    if (!selectElement || !selectElement.options) {
        console.error('Elemento seller no válido:', selectElement);
        return;
    }
    
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    if (!selectedOption) return;
    
    const sellerName = selectedOption.getAttribute('data-name') || '';
    
    const nameField = document.getElementById('seller-name');
    if (nameField) nameField.value = sellerName;
    
    console.log('Seller hidden field updated:', sellerName);
}