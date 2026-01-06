# app/configs.py

# ================= 配电房及设备配置数据源 =================
# 格式说明：
# transformers: [(编号, 名称, 型号), ...]
# circuits: [(编号, 名称, 规格), ...]

ROOM_CONFIGS = [
    {
        'code': 'ROOM_01',
        'name': '1#总配电室',
        'voltage': '10kV',
        'transformers': [
            ('TRANS_001', '1#主变压器', 'SCB10-1000/10'),
            ('TRANS_002', '2#动力变压器', 'SCB10-800/10'),
            ('TRANS_003', '3#照明变压器', 'SCB10-630/10')
        ],
        'circuits': [
            ('AL1_incoming', '1#进线柜回路', '2000A'),
            ('AL2_outlet', '2#动力出线回路', '630A'),
            ('AL3_outlet', '3#照明出线回路', '400A')
        ]
    },
    {
        'code': 'ROOM_02',
        'name': '2#车间配电室',
        'voltage': '10kV',
        'transformers': [
            ('TRANS_004', '4#车间主变', 'SCB10-800/10'),
            ('TRANS_005', '5#流水线变压器A', 'SCB10-630/10'),
            ('TRANS_006', '6#流水线变压器B', 'SCB10-630/10')
        ],
        'circuits': [
            ('AL4_incoming', '2#车间进线', '1250A'),
            ('AL5_outlet', 'A线动力出线', '400A'),
            ('AL6_outlet', 'B线动力出线', '400A')
        ]
    },
    {
        'code': 'ROOM_03',
        'name': '3#研发楼配电室',
        'voltage': '10kV',
        'transformers': [
            ('TRANS_007', '7#研发主变', 'SCB10-630/10'),
            ('TRANS_008', '8#实验室变压器', 'SCB10-500/10'),
            ('TRANS_009', '9#数据中心变压器', 'SCB10-800/10')
        ],
        'circuits': [
            ('AL7_incoming', '3#研发进线', '1000A'),
            ('AL8_outlet', '实验室出线', '630A'),
            ('AL9_outlet', '服务器出线', '800A')
        ]
    }
]