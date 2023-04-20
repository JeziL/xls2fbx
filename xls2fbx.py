import os
import fbx_writer
import capl_channelsync
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
    parser.add_argument("-t", "--template", help="FlexRay 数据库模板文件", required=True)
    parser.add_argument("-o", "--output", help="生成数据库文件的输出路径")
    parser.add_argument("-c", "--capldir", help="生成 CAPL 文件的文件夹路径", default="./CAPL")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args()
    if args.output is None:
        basename, old_suffix = os.path.splitext(args.input_file)
        args.output = basename + ".xml"
    db = XLSDatabase(args.input_file)
    fbx_writer.write(args.template, db, args.output)
    capl_channelsync.generate_CAPL(db, args.capldir)
