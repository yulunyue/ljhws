from typing import List
DIRCTION = [[0, 1], [1, 0], [0, -1], [-1, 0]]
MOVE_NAMES = ['RIGHT', 'DOWN', 'LEFT', 'UP']
CAMERE_SHAPE = [
    [[0, -1], [0, 0], [0, 1]],
    [[-1, 0], [0, 0], [1, 0]],
    [[-1, 0], [0, 0], [0, 1]],
    [[1, 0], [0, 0], [0, 1]],
    [[1, 0], [0, 0], [0, -1]],
    [[-1, 0], [0, 0], [0, -1]],
    [[0, -2], [0, -1], [0, 0], [0, 1], [0, 2]],
    [[-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0]],
    [[-1, 0], [1, 0], [0, 0], [0, 1], [0, -1]],
    [[-1, -1], [-1, 1], [0, 0], [1, 1], [1, -1]]
]


class Cell:
    def __init__(self, x, y, data='*') -> None:
        self.x = x
        self.y = y
        self.is_obstacle = False  # 标识该单元格是否是障碍
        self.land_score = 0  # 单元格摄像头分数
        self.energy = 0  # 机器人移动到该单元格能获取到能量
        self.robot_id = None
        self.owner = -1
        self.warranty_period = 0  # 单元格保护回合数
        self.set_data(data)

    def set_data(self, data):
        if data == '#':
            self.is_obstacle = True
        elif ord(data) >= ord('0') and ord(data) <= ord('9'):
            self.land_score = ord(data) - ord('0')
        elif ord(data) >= ord('a') and ord(data) <= ord('z'):
            self.energy = ord(data) - ord('a')+3
        elif ord(data) >= ord('A') and ord(data) <= ord('Z'):
            self.robot_id = ord(data) - ord('A')


class Player:
    def init(self, player_id, energies_limit,
             camera_unit_energy, obstacles, land_scores,
             max_round=500, warranty_period=20,
             robot_num=4,
             ) -> None:
        self.warranty_period = warranty_period
        self.world_height = len(land_scores)
        self.world_width = len(land_scores[0])
        self.max_round = max_round
        self.max_player_round = max_round/2
        self.worlds: List[List[Cell]] = [[Cell(j, i) for j in range(self.world_width)]
                                         for i in range(self.world_height)]
        self.player_id = player_id
        self.energies_limit = energies_limit
        self.camera_unit_energy = camera_unit_energy
        for o in obstacles:
            self.cell(o['y'], o['x']).is_obstacle = True
        for i in range(len(land_scores)):
            for j in range(len(land_scores[i])):
                if land_scores[i][j]:
                    self.cell(i, j).land_score = land_scores[i][j]
        self.visite_ways = dict()
        self.cameras_cell: List[Cell] = []
        self.robot_num = robot_num

    def cell(self, y, x) -> Cell:
        return self.worlds[y][x]

    def action(self, round, scores, energies, accumulated_energies, robots, occupied_lands):
        self.robots: List = []
        self.others_robots: List = []
        self.current_round = round
        self.scores = scores[:]
        self.accumulated_energies = accumulated_energies[:]
        for o in occupied_lands:
            c = self.cell(o['y'], o['x'])
            c.warranty_period = o["warranty_period"]
            c.owner = o["owner"]
        for robot in robots:
            r = dict(
                player_id=robot["player_id"], robot_id=robot["robot_id"],
                y=robot["y"], x=robot["x"], move="NOP", install_camera=None
            )
            if r['player_id'] == self.player_id:
                self.robots.append(r)
            else:
                self.others_robots.append(r)
            self.cell(r['y'], r['x']).robot_id = r["robot_id"]
        self.all_robots = self.robots + self.others_robots
        for engine in energies:
            self.cell(engine['y'], engine['x']).energy = engine['amount']
        for r in self.robots:
            self.bfs(r)
        return [
            dict(robot_id=r["robot_id"], move=r["move"],
                 install_camera=r["install_camera"])
            for r in self.robots
        ]

    def get_camera_max_score(self, c1: Cell):
        cam_index = None
        max_cam = 0
        cost_max = 0
        for i, yx in enumerate(CAMERE_SHAPE):
            cost = len(CAMERE_SHAPE[i])*self.camera_unit_energy
            if self.accumulated_energies[self.player_id] < cost:
                continue
            cam_score = 0
            for iy, ix in yx:
                y, x = c1.y+iy, c1.x+ix
                if y < 0 or y >= len(self.worlds) or x < 0 or x >= len(self.worlds[0]):
                    # print("gg")
                    cam_score = 0
                    break
                c = self.cell(y, x)
                if c.owner == -1:
                    cam_score += c.land_score
                elif c.owner == self.player_id:
                    pass
                else:
                    if c.warranty_period <= 0:
                        cam_score += 2*c.land_score
            if cam_score > max_cam:
                max_cam = cam_score
                cam_index = i
                cost_max = cost
                # print(c1.y, c1.x, max_cam, cam_index)
        self.accumulated_energies[self.player_id] -= cost_max
        return cam_index

    def bfs(self, r):
        visite_list = [[r["y"], r["x"], 0]]
        visite_map = {
            (r["y"], r["x"]): []
        }
        while len(visite_list):
            y, x, l = visite_list.pop(0)
            c = self.worlds[y][x]
            camera = self.get_camera_max_score(c)
            if camera is not None:
                if l == 0:
                    r["install_camera"] = camera
                else:
                    r["move"] = visite_map[(y, x)][0]
                return
            if c.energy:
                c.energy = 0
                r["move"] = visite_map[(y, x)][0]
                return
            for i, yx in enumerate(DIRCTION):
                next_y, next_x = y+yx[0], x+yx[1]
                if next_y < 0 or next_y >= len(self.worlds) or next_x < 0 or next_x >= len(self.worlds[0]):
                    continue
                if self.cell(next_y, next_x).is_obstacle:
                    continue
                if self.cell(next_y, next_x).robot_id is not None:
                    continue
                if (next_y, next_x) in visite_map:
                    continue
                visite_map[(next_y, next_x)] = visite_map[(y, x)] + \
                    [MOVE_NAMES[i]]
                visite_list.append([next_y, next_x, l+1])


MAP_INFO = '''
A * # * D
* 2 * z *
# * # * #
* 2 * z *
C * # * B
'''
ACTION_MAP = dict(
    n=[0, 0], NOP=[0, 0],
    u=[-1, 0], UP=[-1, 0],
    d=[1, 0], DOWN=[1, 0],
    l=[0, -1], LEFT=[0, -1],
    r=[0, 1], RIGHT=[0, 1]
)


class World:

    def __init__(self) -> None:
        self.players = [Player(), Player()]
        self.scores = [0, 0]
        self.accumulated_energies = [0, 0]
        self.worlds: List[List[Cell]] = []
        self.cells: List[Cell] = []
        self.camera_unit_energy = 1
        self.warranty_period = 20
        self.map_info = MAP_INFO.split('\n')[1:-1]
        self.robot_num = 2
        self.energies_limit = 300
        for i, row in enumerate(self.map_info):
            self.worlds.append([])
            for j, col in enumerate(row.split(" ")):
                self.worlds[-1].append(Cell(j, i, col))
                self.cells.append(self.worlds[-1][-1])
        self.robots = self.get_robots()

    def land_scores(self):
        return [[col.land_score for col in rows] for rows in self.worlds]

    def obstacles(self):
        return [dict(y=c.y, x=c.x) for c in self.cells if c.is_obstacle]

    def get_robots(self):
        return sorted([dict(
            y=c.y, x=c.x,
            actions=[],
            robot_id=c.robot_id,
            player_id=c.robot_id // self.robot_num
        ) for c in self.cells if c.robot_id is not None],
            key=lambda r: r["robot_id"]
        )

    def engines(self):
        return [dict(
            y=c.y, x=c.x,
            amount=c.energy,
        ) for c in self.cells if c.energy]

    def occupied_lands(self):
        return [dict(
            y=c.y, x=c.x,
            owner=c.owner,
            warranty_period=c.warranty_period
        ) for c in self.cells if c.owner != -1]

    def run(self):
        max_round = 6
        for i, p in enumerate(self.players):
            p.init(
                i, self.energies_limit, self.camera_unit_energy,
                self.obstacles(),
                self.land_scores(),
                max_round, robot_num=self.robot_num
            )
        for i in range(max_round):
            p = self.players[i % len(self.players)]
            self.pre()
            actions = p.action(
                i,
                self.scores, self.engines(),
                self.accumulated_energies,
                self.robots,
                self.occupied_lands()
            )
            self.pre_do_action()
            self.do_actions(actions)

    def pre_do_action(self):
        for c in self.cells:
            c.robot_id = None

    def pre(self):
        for c in self.cells:
            if c.warranty_period > 0:
                c.warranty_period -= 1  # 每回合之前保护回合数减1

    def do_actions(self, actions):
        for action in actions:
            info = self.do_action(**action)
            if info:
                raise Exception("do_error", info)

    def put_camera(self, r, install_camera):
        ac_engy = self.accumulated_energies[r["player_id"]]
        cost = len(CAMERE_SHAPE[install_camera])*self.camera_unit_energy
        if ac_engy < cost:
            return f'{ac_engy}<{cost} 放置摄像头{install_camera}能量不足'
        self.accumulated_energies[r["player_id"]] -= cost
        for iy, ix in CAMERE_SHAPE[install_camera]:
            y, x = r["y"]+iy, r["x"]+ix
            if y < 0 or y >= len(self.worlds) or x < 0 or x >= len(self.worlds[0]):
                return f"放置摄像头超出边界:{y}:{x}"
            c: Cell = self.worlds[y][x]
            if c.owner == -1:
                c.owner = r["player_id"]
                self.scores[r["player_id"]] += c.land_score
                c.warranty_period = self.warranty_period
            elif c.owner == r["player_id"]:
                c.warranty_period = self.warranty_period
            else:
                if c.warranty_period == 0:
                    self.scores[c.owner] -= c.land_score
                    c.warranty_period = self.warranty_period
                    c.owner = r["player_id"]
                    self.scores[c.owner] += c.land_score
                    c.warranty_period = self.warranty_period

    def move_to(self, r, iy, ix):
        y, x = r["y"]+iy, r["x"]+ix
        if y < 0 or y >= len(self.worlds) or x < 0 or x >= len(self.worlds[0]):
            return f"机器人移动超出边界:{r} {y},{x}"
        if self.worlds[y][x].is_obstacle:
            return f"机器人碰墙:{r}"
        self.accumulated_energies[r["player_id"]] = min(
            self.accumulated_energies[r["player_id"]]+self.worlds[y][x].energy,
            self.energies_limit
        )
        self.worlds[y][x].energy = 0
        r["y"], r["x"] = y, x

    def do_action(self, robot_id, move="NOP", install_camera=None):
        ret = ""
        r = self.robots[robot_id]

        if install_camera is not None:
            r["actions"].append(str(install_camera))
            ret = self.put_camera(r, install_camera)
        else:
            r["actions"].append(str(move)[0])
            ret = self.move_to(r, *ACTION_MAP[move])
        if self.worlds[r["y"]][r["x"]].robot_id is not None:
            return f"机器人碰撞:{r}"
        self.worlds[r["y"]][r["x"]].robot_id = r["robot_id"]
        return ret

    def print(self):
        print(MAP_INFO)
        for r in self.robots:
            print(f'{chr(ord("A")+r["robot_id"])}:{"".join(r["actions"])}')
        print(
            f'energies:{self.accumulated_energies} scores:{self.scores}')

    def test(self):
        self.run()
        self.print()


if __name__ == "__main__":
    wd = World()
    wd.test()
