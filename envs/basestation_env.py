import numpy as np
import gymnasium as gym
import matplotlib as plt
from klampt.math.autodiff.math_ad import distance

from configs.config_env import *
GRID_NOT_GENERATED_FLAG = -1


# We only consider Y is a rectangular in R^d
class BaseStationEnv(gym.Env):
    def __init__(self, bs_env, area_size=AREA_SIZE, num_base_stations=NUM_BASE_STATIONS,
                 num_users=NUM_USERS, tx_power=TX_POWER, noise_power=NOISE_POWER,shadowing_std = SHADOWING_STD):
        super(BaseStationEnv, self).__init__()

        # 环境参数
        self.env = bs_env
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
        self.users = np.array([[point['x'], point['y'],0] for point in self.env.users])
        self.bs = np.array([[point['x'], point['y'],point['z']] for point in self.env.bs])


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

    def _calculate_sinr(self):
        """计算所有用户的平均 SINR，包括阴影衰落"""

        def dbm_to_watt(dbm):
            return 10 ** ((dbm - 30) / 10)

        def pathloss_los(distance, shadowing_std):
            d_2d = np.sqrt(distance ** 2 - (H_BS - H_UE) ** 2)
            if d_2d < D_BP:
                PL = 32.4 + 21 * np.log10(distance) + 20 * np.log10(F)
            else:
                PL = 32.4 + 40 * np.log10(distance) + 20 * np.log10(F) - 9.5 * np.log10((D_BP) ** 2 + (H_BS - H_UE) ** 2)
            shadowing = np.random.normal(0, shadowing_std , size=distance.shape)
            PL += shadowing
            return PL

        def pathloss_nlos(distance, shadowing_std):
            PL = 22.4 + 35.3 * np.log10(distance) + 21.3 * np.log10(F)
            shadowing = np.random.normal(0, shadowing_std, size=distance.shape)
            PL += shadowing
            return PL

        def path_loss(user, distance, exponent, shadowing_std):
            # 添加阴影衰落,添加 LOS 与 NLOS 的不同计算方法
            """
            PL_LOS = PL1 else PL2  if 10<d_2D<d_BP
            PL1 = 28+22*log10(d_3D)+20log10(f)
            PL2 = 28+40*log10(d_3D)+20log10(f)-9log10((d_BP)^2+(h_BS-h_UE)^2)   shadowing = 4

            PL_NLOS = 13.54+39.08log10(d_3D)+20log10(fc)-0.6(h_UE-1.5)  shadowing =6
            """
            pathloss = []
            for i in range(len(self.env.bs)):
                if_obstacle = self.env.check_obstacle(user,self.bs[i])
                print(if_obstacle)
                if if_obstacle == False:
                    PL = pathloss_los(distance[i],4)
                    pathloss.append(PL)
                else:
                    PL_NLOS = pathloss_nlos(distance[i],7.82)
                    PL_LOS = pathloss_los(distance[i],4)
                    PL = max(PL_NLOS, PL_LOS)
                    pathloss.append(PL)
            print(pathloss)
            return  np.array(pathloss)

        sinr_values = []
        for user in self.users:   # {x:x,y:y}
            distances = np.linalg.norm(self.bs - user, axis=1)
            print(f'distance\n{distances}')

            path_losses = path_loss(user, distances, self.path_loss_exponent, self.shadowing_std)  # 包含阴影衰落
            received_powers = dbm_to_watt(self.tx_power - path_losses)
            # # Rayleigh 衰落模拟
            # A = np.random.rayleigh(scale=1.0, size=1)
            # P_received = A ** 2  # Rayleigh 衰落
            received_powers = received_powers
            signal_power = np.max(received_powers)
            interference_power = np.sum(received_powers) - signal_power
            noise_power_watt = dbm_to_watt(self.noise_power)
            sinr = signal_power / (interference_power + noise_power_watt)
            sinr_values.append(sinr)

        return sinr_values



