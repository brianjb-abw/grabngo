import csv
from pathlib import Path
from handlers.dexter import dexterProc
from handlers.loadtrail import loadtrailProc

IN_DIR = Path('IN')
OUT_DIR = Path('OUT')
FIELDNAMES = ['mfr', 'invoice_number', 'invoice_date', 'qty',
              'item_number', 'description', 'unit_price', 'extension']


def get_existing_invoice_numbers(csv_path):
    if not csv_path.exists():
        return set()
    numbers = set()
    try:
        with open(csv_path, newline='') as f:
            for row in csv.DictReader(f):
                numbers.add(row['invoice_number'])
    except Exception:
        pass
    return numbers


def main():
    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / 'output.csv'

    existing_invoices = get_existing_invoice_numbers(out_path)
    need_header = not out_path.exists() or out_path.stat().st_size == 0

    total_rows = 0

    for pdf in sorted(IN_DIR.glob('*.pdf')):
        name = pdf.name.upper()
        if name.startswith('LT '):
            rows, stated_total = loadtrailProc(pdf)
        elif name.startswith('DX') or name.startswith('D-'):
            rows, stated_total = dexterProc(pdf)
        else:
            continue

        if not rows:
            continue

        invoice_number = rows[0]['invoice_number']

        if invoice_number in existing_invoices:
            print(f"WARNING: possible duplicate data — invoice {invoice_number} already exists in output file")

        with open(out_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if need_header:
                writer.writeheader()
                need_header = False
            writer.writerows(rows)

        existing_invoices.add(invoice_number)
        total_rows += len(rows)

        running_total = round(sum(float(r['extension']) for r in rows), 2)

        if stated_total is not None and round(running_total, 2) == round(stated_total, 2):
            print(f"Processed invoice {invoice_number}  total:  ${running_total:,.2f}")
        elif stated_total is not None:
            print(f"ALERT: math problem on invoice {invoice_number}")
            print(f"  Invoice states:   ${stated_total:,.2f}")
            print(f"  Rows calculated:  ${running_total:,.2f}")
        else:
            print(f"Processed invoice {invoice_number}  total:  ${running_total:,.2f}")

    print(f"\nWrote {total_rows} rows to {out_path}")


if __name__ == '__main__':
    main()
