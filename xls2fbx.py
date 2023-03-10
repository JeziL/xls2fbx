import fbx_writer
from xls_dbreader import XLSDatabase
from argparse import ArgumentParser

__version__ = "0.1.0"

if __name__ == "__main__":
    parser = ArgumentParser(
        prog="xls2fbx",
        description="从 Excel 工作簿生成 FlexRay FIBEX 数据库",
        epilog="Deployment icons created by Uniconlabs - Flaticon",
    )
    parser.add_argument("input_file", help="Excel 工作簿文件")
    parser.add_argument("-t", "--template", help="FlexRay 数据库模板文件")
    parser.add_argument("-o", "--output", help="生成数据库文件的输出路径")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args()
    db = XLSDatabase(args.input_file)
    fbx_writer.write(args.template, db, args.output)
