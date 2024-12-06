import numpy as np
import gymnasium as gym
import matplotlib as plt
from configs.config_env import *
GRID_NOT_GENERATED_FLAG = -1


class Grid:
    def __init__(self, dim_Y, lb_Y, ub_Y):
        self.dim_Y = dim_Y
        self.lb_Y = lb_Y
        self.ub_Y = ub_Y
        self.fineness = GRID_NOT_GENERATED_FLAG
        self.grid = np.empty((1,))
        self.size = 0

    # Reset the grid.
    def reset(self):
        self.fineness = GRID_NOT_GENERATED_FLAG
        self.grid = np.empty((1,))
        self.size = 0
        return

    # Generate the grid.
    def generate(self, fineness=100) -> np.ndarray:
        if self.fineness == fineness:
            # The grid has been computed.
            return self.grid
        elif self.fineness != -1:
            self.reset()

        self.fineness = fineness
        self.size = (self.fineness + 1) ** self.dim_Y

        coordinate_lst = []
        index_array = np.indices(list(self.dim_Y * [self.fineness + 1]))
        for i in range(self.dim_Y):
            coordinate_lst.append(index_array[i].reshape(-1) *
                                  ((self.ub_Y[i] - self.lb_Y[i]) / self.fineness) + self.lb_Y[i])
        self.grid = np.stack(list(coordinate_lst), axis=1)
        return self.grid

# We only consider Y is a rectangular in R^d
class BaseStationEnv(gym.Env):
    def __init__(self, area_size=AREA_SIZE, num_base_stations=NUM_BASE_STATIONS,
                 num_users=NUM_USERS, tx_power=TX_POWER, noise_power=NOISE_POWER,shadowing_std = SHADOWING_STD):
        super(BaseStationEnv, self).__init__()

        # 环境参数
        self.area_size = area_size  # 区域大小
        self.num_base_stations = num_base_stations  # 基站数量
        self.num_users = num_users  # 用户数量
        self.tx_power = tx_power  # 基站发射功率 (dBm)
        self.noise_power = noise_power  # 热噪声功率 (dBm)
        self.path_loss_exponent = PATH_LOSS_EXPONENT  # 路径损耗指数
        self.shadowing_std = shadowing_std  # 阴影衰落标准差 (dB)

        # 状态空间 (基站和用户的位置)
        self.observation_space = gym.spaces.Box(
            low=0, high=area_size, shape=(num_base_stations + num_users, 2), dtype=np.float32
        )

        # 动作空间 (基站位置调整)
        self.action_space = gym.spaces.Box(
            low=-100, high=100, shape=(num_base_stations, 2), dtype=np.float32
        )

        # 初始化用户和基站位置
        self.users = np.random.uniform(0, area_size, (num_users, 2))
        self.base_stations = np.random.uniform(0, area_size, (num_base_stations, 2))

    def reset(self):
        """重置环境"""
        self.users = np.random.uniform(0, self.area_size, (self.num_users, 2))
        self.base_stations = np.random.uniform(0, self.area_size, (self.num_base_stations, 2))
        return self._get_observation()

    def step(self, action):
        """环境状态更新"""
        # 更新基站位置
        self.base_stations += action
        self.base_stations = np.clip(self.base_stations, 0, self.area_size)  # 限制基站在区域内

        # 计算奖励 (以平均 SINR 为奖励)
        avg_sinr = self._calculate_avg_sinr()
        reward = avg_sinr

        # 终止条件 (这里假设单步不终止，可根据实际需求调整)
        done = False

        return self._get_observation(), reward, done, {}

    def render(self, mode='human'):
        """可视化环境"""
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 8))
        plt.scatter(self.users[:, 0], self.users[:, 1], c='blue', label='Users')
        plt.scatter(self.base_stations[:, 0], self.base_stations[:, 1], c='red', label='Base Stations', s=100)
        plt.xlim(0, self.area_size)
        plt.ylim(0, self.area_size)
        plt.title('Base Station Deployment')
        plt.xlabel('X-coordinate (m)')
        plt.ylabel('Y-coordinate (m)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def _get_observation(self):
        """获取环境的状态表示"""
        return np.vstack((self.base_stations, self.users))

    def _calculate_avg_sinr(self):
        """计算所有用户的平均 SINR，包括阴影衰落"""

        def dbm_to_watt(dbm):
            return 10 ** ((dbm - 30) / 10)

        def path_loss(distance, exponent, shadowing_std):
            # 添加阴影衰落
            shadowing = np.random.normal(0, shadowing_std, size=distance.shape)
            return 10 * exponent * np.log10(distance + 1e-9) + shadowing

        avg_sinr = 0
        for user in self.users:
            distances = np.linalg.norm(self.base_stations - user, axis=1)
            path_losses = path_loss(distances, self.path_loss_exponent, self.shadowing_std)  # 包含阴影衰落
            received_powers = dbm_to_watt(self.tx_power - path_losses)
            signal_power = np.max(received_powers)
            interference_power = np.sum(received_powers) - signal_power
            noise_power_watt = dbm_to_watt(self.noise_power)
            sinr = signal_power / (interference_power + noise_power_watt)
            avg_sinr += np.log2(1 + sinr)  # 使用 Shannon Capacity (bps/Hz)

        return avg_sinr / self.num_users


# 测试环境
env = BaseStationEnv()

# 重置环境
obs = env.reset()

# 随机动作测试
for _ in range(10):
    action = env.action_space.sample()
    obs, reward, done, _ = env.step(action)
    print(f"Reward (Average SINR): {reward:.2f}")
    env.render()