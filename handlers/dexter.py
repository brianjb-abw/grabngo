import re
import PyPDF2

# Matches the numeric data columns: orig_qty EA $unit_price $extended inv_qty item_number
_DATA_LINE = re.compile(
    r'(\d[\d,.]*)\s+EA\s+\$(\d[\d,.]*)\s+\$(\d[\d,.]*)\s+(\d[\d,.]*)\s+(\S+)\s*$'
)
_TOTAL = re.compile(r'Total Order Amount\$?([\d,]+\.\d{2})')


def _parse_num(s):
    return float(s.replace(',', ''))


def _parse_page(page_text, invoice_number, invoice_date):
    lines = page_text.split('\n')

    # Find where the items table starts (line after the column header)
    start = 0
    for i, line in enumerate(lines):
        if 'Customer Item Reference' in line:
            start = i + 1
            break

    rows = []
    description = None
    desc_parts = []
    i = start

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        i += 1

        if not stripped:
            continue

        # Stop before backorder section or totals footer
        if 'Backorders' in stripped or 'B/O Qty' in stripped:
            break
        if stripped.startswith('Net Amount'):
            break

        if description is None:
            description = stripped
            desc_parts = [stripped]
            continue

        m = _DATA_LINE.search(stripped)
        if m:
            inv_qty = int(float(m.group(4).replace(',', '')))
            if inv_qty > 0:
                rows.append({
                    'mfr': 'DX',
                    'invoice_number': invoice_number,
                    'invoice_date': invoice_date,
                    'qty': inv_qty,
                    'item_number': m.group(5),
                    'description': description,
                    'desc_full': ' '.join(desc_parts),
                    'unit_price': f'{_parse_num(m.group(2)):.2f}',
                    'extension': f'{_parse_num(m.group(3)):.2f}',
                })
            # Consume through the COO line then reset for next item
            for _ in range(5):
                if i >= len(lines):
                    break
                coo = lines[i].strip()
                i += 1
                if 'COO:' in coo:
                    break
            description = None
            desc_parts = []
        else:
            desc_parts.append(stripped)

    return rows


def dexterProc(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        pages = [p.extract_text() or '' for p in reader.pages]

    m = re.search(r'INV-(\d+)\n(\d{1,2}/\d{1,2}/\d{4})', pages[0])
    invoice_number = m.group(1)
    invoice_date = m.group(2)

    rows = []
    for page_text in pages:
        rows.extend(_parse_page(page_text, invoice_number, invoice_date))

    full_text = '\n'.join(pages)
    m = _TOTAL.search(full_text)
    stated_total = _parse_num(m.group(1)) if m else None

    return rows, stated_total
