# 1. 基础参数设置
AREA_SIZE = 2000  # 区域边长 (单位：米)
NUM_BASE_STATIONS = 5  # 基站数量
NUM_USERS = 50  # 用户数量
TX_POWER = 44  # 基站发射功率 (单位：dBm)  25W
NOISE_POWER = -100  # 热噪声功率 (单位：dBm)
PATH_LOSS_EXPONENT = 3  # 路径损耗指数
SHADOWING_STD = 8  # 阴影衰落标准差 (单位：dB)
MESH_NUM = 10000   # 生成地图的网格精细程度
d_BP = 1200   # 参考距离