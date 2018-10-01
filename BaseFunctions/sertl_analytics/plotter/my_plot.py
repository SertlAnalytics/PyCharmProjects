import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, Polygon, Rectangle, Arrow, Ellipse


class MyPlotHelper:
    @staticmethod
    def get_xy_for_tick_list_and_function(tick_list: list, func):
        x = [tick.f_var for tick in tick_list]
        y = [func(tick.f_var) for tick in tick_list]
        return list(zip(x, y))

    @staticmethod
    def get_polygon_for_tick_list(tick_list: list, func, closed: bool = True):
        xy = MyPlotHelper.get_xy_for_tick_list_and_function(tick_list, func)
        return Polygon(np.array(xy), closed=closed)

    @staticmethod
    def get_xy_parameter_for_tick_function_list(tick_list: list, func_list, closed: bool = True):
        x = [tick.f_var for tick in tick_list]
        y = [round(func(tick_list[ind].f_var),2) for ind, func in enumerate(func_list)]
        return list(zip(x, y))

    @staticmethod
    def get_xy_parameter_for_replay_list(tick_list: list, for_buying: bool):
        x = [tick.time_stamp for tick in tick_list]
        y = [tick.breakout_value if for_buying else tick.limit_value for tick in tick_list]
        for tick in reversed(tick_list):
            x.append(tick.time_stamp)
            y.append(tick.wrong_breakout_value if for_buying else tick.stop_loss_value)
        # print('list(zip(x, y))={}'.format(list(zip(x, y))))
        return list(zip(x, y))
