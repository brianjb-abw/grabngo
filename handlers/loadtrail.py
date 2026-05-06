import re
import PyPDF2

_LINE_ITEM = re.compile(r'^EACH\s+([\d,]+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$')
_ITEM_NUM = re.compile(r'([A-Z]?\d{5,}(?:-[A-Z0-9]+)*)$')
_TOTAL = re.compile(r'Total:\s*([\d,]+\.\d{2})')


def _parse_num(s):
    return float(s.replace(',', ''))


def _split_desc_item(line):
    m = _ITEM_NUM.search(line)
    if m:
        return line[:m.start()].strip(' @\t'), m.group(1)
    return line, ''


def loadtrailProc(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        pages = [p.extract_text() for p in reader.pages]

    first_lines = [l.strip() for l in pages[0].split('\n') if l.strip()]
    invoice_number = first_lines[0]
    invoice_date = first_lines[1]

    rows = []
    for page_text in pages:
        lines = [l.strip() for l in page_text.split('\n') if l.strip()]
        i = 0
        while i < len(lines):
            m = _LINE_ITEM.match(lines[i])
            if m and i + 1 < len(lines):
                qty = int(m.group(1).replace(',', ''))
                extension = _parse_num(m.group(2))
                unit_price = _parse_num(m.group(3))
                if qty > 0:
                    description, item_number = _split_desc_item(lines[i + 1])
                    rows.append({
                        'mfr': 'LT',
                        'invoice_number': invoice_number,
                        'invoice_date': invoice_date,
                        'qty': qty,
                        'item_number': item_number,
                        'description': description,
                        'unit_price': f'{unit_price:.2f}',
                        'extension': f'{extension:.2f}',
                    })
                i += 2
            else:
                i += 1

    full_text = '\n'.join(pages)
    m = _TOTAL.search(full_text)
    stated_total = _parse_num(m.group(1)) if m else None

    return rows, stated_total
