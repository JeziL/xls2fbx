import fbx_writer
from xls_dbreader import XLSDatabase
from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser(
        prog="xls2fbx",
        description="Generate FIBEX FlexRay database from Excel workbook.",
    )
    parser.add_argument("input_file", help="Input Excel file path.")
    parser.add_argument("-t", "--template", help="FIBEX template file path.")
    parser.add_argument("-o", "--output", help="Output file path.")
    args = parser.parse_args()
    db = XLSDatabase(args.input_file)
    fbx_writer.write(args.template, db, args.output)
