import re
import PyPDF2
from decimal import Decimal, ROUND_HALF_UP

_ITEM_NUM = re.compile(r'^[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+$')
_INT = re.compile(r'^(\d+)$')
_CURRENCY = re.compile(r'^\$([\d,]+\.\d{2})$')

_INVOICE_NUM = re.compile(r'Invoice\s*#:\s*(\d+)')
_INVOICE_DATE = re.compile(r'Date:\s*(\d{4}-\d{2}-\d{2})')
_SUBTOTAL = re.compile(r'Subtotal:\s*\$?([\d,]+\.\d{2})')

_CENT = Decimal('0.01')
_MIL = Decimal('0.001')


def _parse_num(s):
    return float(s.replace(',', ''))


def _parse_decimal(s):
    return Decimal(s.replace(',', ''))


def _clean_desc(s):
    return re.sub(r'\s+', ' ', s).strip()


def _parse_page(lines, invoice_number, invoice_date):
    rows = []

    start = 0
    for j, l in enumerate(lines):
        if l == 'Extension':
            start = j + 1
            break

    i = start
    while i < len(lines):
        line = lines[i]

        if line.startswith('Subtotal') or line.startswith('FREIGHT'):
            break

        if _ITEM_NUM.match(line) and i + 8 < len(lines):
            item_number = line
            desc_line = lines[i + 1]
            shipped_m = _INT.match(lines[i + 3])
            unit_m = _CURRENCY.match(lines[i + 7])
            ext_m = _CURRENCY.match(lines[i + 8])

            if shipped_m and unit_m and ext_m:
                qty = int(shipped_m.group(1))
                printed_unit_price = _parse_decimal(unit_m.group(1))
                extension = _parse_decimal(ext_m.group(1))

                if qty > 0:
                    # line item accuracy check
                    unit_price_calc = extension / qty
                    unit_price_calc = unit_price_calc.quantize(_MIL, rounding=ROUND_HALF_UP)
                    if abs(unit_price_calc - printed_unit_price) > .005:
                        print(f"err: accuracy, invoice num {invoice_number}, item num {item_number}")

                    # line append
                    rows.append({
                        'mfr': 'BB',
                        'invoice_number': invoice_number,
                        'invoice_date': invoice_date,
                        'qty': qty,
                        'item_number': item_number,
                        'description': _clean_desc(desc_line),
                        'desc_full': '',
                        'unit_price': f'{unit_price_calc:.3f}',
                        'extension': f'{extension:.2f}',
                    })

                i += 9
                continue

        i += 1

    return rows


def badboyProc(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        pages = [p.extract_text() or '' for p in reader.pages]

    full_text = '\n'.join(pages).replace('\t', ' ')

    m = _INVOICE_NUM.search(full_text)
    invoice_number = str(int(m.group(1))) if m else ''

    m = _INVOICE_DATE.search(full_text)
    invoice_date = m.group(1) if m else ''

    rows = []
    for page_text in pages:
        lines = [l.replace('\t', ' ').strip() for l in page_text.split('\n')]
        lines = [l for l in lines if l]
        rows.extend(_parse_page(lines, invoice_number, invoice_date))

    m = _SUBTOTAL.search(full_text)
    stated_total = _parse_num(m.group(1)) if m else None

    return rows, stated_total
