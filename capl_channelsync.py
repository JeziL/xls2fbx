import os


def generate_CAPL(db, capl_path):
    for ecu in db.ecus:
        file_path = os.path.join(capl_path, f"{ecu.name}.can")
        with open(file_path, "w") as f:
            f.write(
"""/*@!Encoding:936*/
includes
{
  
}

variables
{
  byte count = 0;
}
"""
                    )
            for frame in ecu.frames:
                f.write(f"\n/****** {frame.name} ******/\n")
                for signal in frame.signals:
                    f.write(
f"""
on signal {frame.name}_Ch_A::{signal.name} {{
  ${frame.name}_Ch_B::{signal.name} = this;
}}
"""
                    )
                    if signal.name.split("_")[-1] == "COUNT":
                        f.write(
f"""
on frFrame {frame.name}_Ch_A {{
  count = ${frame.name}_Ch_A::{signal.name};
  count++;
  ${frame.name}_Ch_A::{signal.name} = count;
}}
"""
                        )
