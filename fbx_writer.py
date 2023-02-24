from lxml import etree
from copy import deepcopy
from lxml.builder import ElementMaker


id_counters = {
    "ECU": 0,
    "Frame": 0,
    "Signal": 0,
    "FrameTriggering": 0,
    "Controller": 0,
    "Connector": 0,
    "OutputPort": 0,
    "SignalInstance": 0,
    "Coding": 0,
    "CompuMethod": 0,
}
NS = {
    "fx": "http://www.asam.net/xml/fbx",
    "ho": "http://www.asam.net/xml",
    "flexray": "http://www.asam.net/xml/fbx/flexray",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
E = ElementMaker(nsmap=NS, namespace="http://www.asam.net/xml/fbx")
E_HO = ElementMaker(nsmap=NS, namespace="http://www.asam.net/xml")
E_FLR = ElementMaker(nsmap=NS, namespace="http://www.asam.net/xml/fbx/flexray")


def assign_fbx_id(node_type):
    id_counters[node_type] += 1
    return f"{node_type}_{id_counters[node_type]}"


def write_ECU(xml, ecu):
    key_slots = []
    for frame in ecu.frames:
        # 分配帧 ID、时序 ID
        frame.fbx_id = assign_fbx_id("Frame")
        frame.ft_fbx_id = assign_fbx_id("FrameTriggering")
        # 记录启动帧 Slot
        if frame.is_startup:
            key_slots.append(frame.slot)
        # 构建并向两个 Channel 增加该帧的 Frame Trigger（时序）
        ft = getattr(E, "FRAME-TRIGGERING")(
            E.TIMINGS(
                getattr(E, "ABSOLUTELY-SCHEDULED-TIMING")(
                    getattr(E, "SLOT-ID")(
                        str(frame.slot),
                        {f"{{{NS['xsi']}}}type": "flexray:SLOT-ID-TYPE"},
                    ),
                    getattr(E, "BASE-CYCLE")(
                        str(frame.base_cycle),
                        {f"{{{NS['xsi']}}}type": "flexray:BASE-CYCLE-TYPE"},
                    ),
                    getattr(E, "CYCLE-REPETITION")(
                        str(frame.cycle_rep),
                        {f"{{{NS['xsi']}}}type": "flexray:CYCLE-REPETITION-TYPE"},
                    ),
                )
            ),
            getattr(E, "FRAME-REF")({"ID-REF": frame.fbx_id}),
            ID=frame.ft_fbx_id,
        )
        channel_fts = xml.xpath("//fx:FRAME-TRIGGERINGS", namespaces=NS)
        for ch_no, channel_ft in enumerate(channel_fts):
            if frame.channels[ch_no]:
                channel_ft.insert(0, deepcopy(ft))

    # 分配节点 ID、控制参数 ID
    ecu.fbx_id = assign_fbx_id("ECU")
    ecu.ctrl_fbx_id = assign_fbx_id("Controller")

    # 构建 ECU 节点
    ecu_node = E.ECU(
        getattr(E_HO, "SHORT-NAME")(ecu.name),
        E_HO.DESC(ecu.desc),
        E.CONTROLLERS(
            E.CONTROLLER(getattr(E_HO, "SHORT-NAME")(ecu.name), ID=ecu.ctrl_fbx_id)
        ),
        E.CONNECTORS(),
        ID=ecu.fbx_id,
    )
    ctrl = ecu_node.find(".//fx:CONTROLLER", namespaces=NS)

    # 复制模板默认 Controller 参数
    default_params = xml.find("//xls2fbx/ControllerValues")
    for param in default_params:
        ctrl.insert(0, deepcopy(param))

    # 若有，添加本 ECU 涉及的关键帧声明
    ks_usage = etree.SubElement(ctrl, etree.QName(NS["flexray"], "KEY-SLOT-USAGE"))
    if len(key_slots) > 0:
        for key_slot in key_slots:
            etree.SubElement(
                ks_usage, etree.QName(NS["flexray"], "STARTUP-SYNC")
            ).text = str(key_slot)
    else:
        etree.SubElement(ks_usage, etree.QName(NS["flexray"], "NONE"))

    # 添加本 ECU 分别向两个 Channel 的 Connector
    cncts = ecu_node.find(".//fx:CONNECTORS", namespaces=NS)
    wakeup_channel = 1 if ecu.channels[1] else 0  # 若同时连接双通道，则 B 通道为唤醒通道
    for ch_no in range(2):
        if not ecu.channels[ch_no]:
            continue
        cnct = E.CONNECTOR(
            getattr(E, "CHANNEL-REF")({"ID-REF": f"Channel_{ch_no + 1}"}),
            getattr(E, "CONTROLLER-REF")({"ID-REF": ecu.ctrl_fbx_id}),
            E.OUTPUTS(),
            getattr(E_FLR, "WAKE-UP-CHANNEL")(
                "true" if ch_no == wakeup_channel else "false"
            ),
            ID=assign_fbx_id("Connector"),
        )
        # 添加本 ECU 下所有帧的时序引用
        outputs = cnct.find(".//fx:OUTPUTS", namespaces=NS)
        for frame in ecu.frames:
            if not frame.channels[ch_no]:
                continue
            op = etree.SubElement(
                outputs,
                etree.QName(NS["fx"], "OUTPUT-PORT"),
                {"ID": assign_fbx_id("OutputPort")},
            )
            etree.SubElement(
                op,
                etree.QName(NS["fx"], "FRAME-TRIGGERING-REF"),
                {"ID-REF": frame.ft_fbx_id},
            )
        cncts.insert(0, cnct)

    # 添加 ECU 节点
    ecus = xml.find("//fx:ECUS", namespaces=NS)
    ecus.insert(0, ecu_node)


def write_Signal(xml, signal):
    # 分配 Coding ID
    signal.coding_fbx_id = assign_fbx_id("Coding")

    # 添加 Signal 节点
    signal_node = E.SIGNAL(
        getattr(E_HO, "SHORT-NAME")(signal.name),
        E_HO.DESC(signal.desc),
        getattr(E, "CODING-REF")({"ID-REF": signal.coding_fbx_id}),
        ID=signal.fbx_id,
    )
    signals = xml.find("//fx:SIGNALS", namespaces=NS)
    signals.insert(0, signal_node)

    # 添加对应 Coding 节点
    coding_node = E.CODING(
        getattr(E_HO, "SHORT-NAME")(signal.coding_fbx_id),
        getattr(E_HO, "CODED-TYPE")(
            getattr(E_HO, "BIT-LENGTH")(str(signal.length)),
            {
                "CATEGORY": "STANDARD-LENGTH-TYPE",
                f"{{{NS['ho']}}}BASE-DATA-TYPE": f"A_{signal.data_type.upper()}",
            },
        ),
        getattr(E_HO, "COMPU-METHODS")(),
        ID=signal.coding_fbx_id,
    )
    compus = coding_node.find(".//ho:COMPU-METHODS", namespaces=NS)
    # 设置线性 CompuMethod
    if (
        (signal.factor is not None)
        and (signal.offset is not None)
        and (signal.factor != 1 or signal.offset != 0)
    ):
        compu_method = getattr(E_HO, "COMPU-METHOD")(
            getattr(E_HO, "SHORT-NAME")(assign_fbx_id("CompuMethod")),
            E_HO.CATEGORY("LINEAR"),
            getattr(E_HO, "COMPU-INTERNAL-TO-PHYS")(
                getattr(E_HO, "COMPU-SCALES")(
                    getattr(E_HO, "COMPU-SCALE")(
                        getattr(E_HO, "COMPU-RATIONAL-COEFFS")(
                            getattr(E_HO, "COMPU-NUMERATOR")(
                                E_HO.V(str(signal.offset)), E_HO.V(str(signal.factor))
                            )
                        )
                    )
                )
            ),
        )
        compus.insert(0, compu_method)
    # 设置 TextTable
    if signal.text_table:
        compu_method = getattr(E_HO, "COMPU-METHOD")(
            getattr(E_HO, "SHORT-NAME")(assign_fbx_id("CompuMethod")),
            E_HO.CATEGORY("TEXTTABLE"),
            getattr(E_HO, "COMPU-INTERNAL-TO-PHYS")(getattr(E_HO, "COMPU-SCALES")()),
        )
        scales = compu_method.find(".//ho:COMPU-SCALES", namespaces=NS)
        for k, v in signal.text_table.items():
            scale = getattr(E_HO, "COMPU-SCALE")(
                getattr(E_HO, "LOWER-LIMIT")(str(k)),
                getattr(E_HO, "UPPER-LIMIT")(str(k)),
                getattr(E_HO, "COMPU-CONST")(E_HO.VT(str(v))),
            )
            scales.insert(0, scale)
        compus.insert(0, compu_method)

    codings = xml.find("//fx:CODINGS", namespaces=NS)
    codings.insert(0, coding_node)


def write_Frame(xml, frame):
    # 构建 Frame 节点
    frame_node = E.FRAME(
        getattr(E_HO, "SHORT-NAME")(frame.name),
        E_HO.DESC(frame.desc),
        getattr(E, "BYTE-LENGTH")(str(frame.length)),
        getattr(E, "FRAME-TYPE")("APPLICATION"),
        getattr(E, "SIGNAL-INSTANCES")(),
        ID=frame.fbx_id,
    )

    # 遍历 Signals
    sig_inss = frame_node.find(".//fx:SIGNAL-INSTANCES", namespaces=NS)
    for signal in frame.signals:
        # 分配 Signal ID
        signal.fbx_id = assign_fbx_id("Signal")

        # 添加 Frame 中的 Signal Instances
        sig_ins = getattr(E, "SIGNAL-INSTANCE")(
            getattr(E, "BIT-POSITION")(str(signal.start_bit)),
            getattr(E, "IS-HIGH-LOW-BYTE-ORDER")("true"),
            getattr(E, "SIGNAL-REF")({"ID-REF": signal.fbx_id}),
            ID=assign_fbx_id("SignalInstance"),
        )
        sig_inss.insert(0, sig_ins)

        # 添加 Signal 节点
        write_Signal(xml, signal)

    frames = xml.find("//fx:FRAMES", namespaces=NS)
    frames.insert(0, frame_node)


def write(template, database, output):
    # 载入模板
    xml = etree.parse(template)

    # 写入数据库
    for ecu in database.ecus:
        write_ECU(xml, ecu)
        for frame in ecu.frames:
            write_Frame(xml, frame)

    # 删除模板内容
    template_info = xml.find("//xls2fbx")
    xml.getroot().remove(template_info)

    # 输出文件
    xml.write(output, pretty_print=False)
