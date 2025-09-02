// static/js/sales.js
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar Select2 para búsqueda
    $('.select2-busqueda').select2({
        placeholder: "🔎 Seleccione un elemento",
        language: "es",
        width: '100%',
        minimumInputLength: 0,
        allowClear: true,
        theme: 'default'
    });

    // Actualizar datos del alumno
    function updateCustomerData(selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const customerName = selectedOption?.getAttribute('data-name') || '';
        const customerEnrollment = selectedOption?.getAttribute('data-enrollment') || '';
        
        document.getElementById('customer-name').value = customerName;
        document.getElementById('customer-enrollment').value = customerEnrollment;
    }

    // Actualizar datos del vendedor
    function updateSellerData(selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const sellerName = selectedOption?.getAttribute('data-name') || '';
        document.getElementById('seller-name').value = sellerName;
    }

    // Inicializar datos de selects
    function initSelectData() {
        const customerSelect = document.getElementById('customer-select');
        const sellerSelect = document.getElementById('seller-select');
        
        if (customerSelect) {
            updateCustomerData(customerSelect);
            customerSelect.addEventListener('change', function() {
                updateCustomerData(this);
            });
        }
        
        if (sellerSelect) {
            updateSellerData(sellerSelect);
            sellerSelect.addEventListener('change', function() {
                updateSellerData(this);
            });
        }
    }

    // Funciones existentes para items
    function addRowFromProduct(p){
        addRow(p.sku, p.description, 1, p.price, p.tax_rate);
    }
    
    function addRow(sku="", desc="", qty=1, price=0, tax=0){
        const tbody = document.getElementById('items-body');
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input value="${sku}" readonly oninput="sync()" /></td>
            <td><input value="${desc}" readonly oninput="sync()" style="width:100%"/></td>
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
            const [sku, desc, qty, price, taxrate] = [...tr.querySelectorAll('input')].map(i=>i.value);
            const q = parseFloat(qty||0), p = parseFloat(price||0), t = parseFloat(taxrate||0);
            const line = Math.max(0, (q*p) * (1+t));
            tr.querySelector('[data-importe]').textContent = line.toFixed(2);
            subtotal += q*p;
            tax += (q*p)*t;
            total += line;
        });
        document.getElementById('t-subtotal').textContent = subtotal.toFixed(2);
        document.getElementById('t-tax').textContent = tax.toFixed(2);
        document.getElementById('t-total').textContent = total.toFixed(2);

        // empaquetar arrays para POST
        const hidden = document.getElementById('hidden-arrays');
        hidden.innerHTML = '';
        rows.forEach(tr=>{
            const [sku, desc, qty, price, taxrate] = [...tr.querySelectorAll('input')].map(i=>i.value);
            ["sku","desc","qty","price","tax"].forEach((k,idx)=>{
                const v = [sku,desc,qty,price,taxrate][idx];
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = k + '[]';
                input.value = v;
                hidden.appendChild(input);
            });
        });
    }

    // inserta rápido con Enter desde el buscador
    document.addEventListener('click', e=>{
        const li = e.target.closest('[data-sku]');
        if(li){ addRowFromProduct(JSON.parse(li.dataset.payload)); }
    });

    // Inicializar todo
    initSelectData();
});