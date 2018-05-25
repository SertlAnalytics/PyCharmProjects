"""
Illustrate the figure and axes enter and leave events by changing the
frame colors on enter and leave
https://matplotlib.org/users/event_handling.html#event-connections
"""
import numpy as np
import matplotlib.pyplot as plt


def enter_axes(event):
    print('enter_axes', event.inaxes)
    event.inaxes.patch.set_facecolor('yellow')
    event.canvas.draw()


def leave_axes(event):
    print('leave_axes', event.inaxes)
    event.inaxes.patch.set_facecolor('white')
    event.canvas.draw()


def enter_figure(event):
    print('enter_figure', event.canvas.figure)
    event.canvas.figure.patch.set_facecolor('red')
    event.canvas.draw()


def leave_figure(event):
    print('leave_figure', event.canvas.figure)
    event.canvas.figure.patch.set_facecolor('grey')
    event.canvas.draw()


def mouse_hover_over_figure():
    fig1 = plt.figure()
    fig1.suptitle('mouse hover over figure or axes to trigger events')
    ax1 = fig1.add_subplot(211)
    ax2 = fig1.add_subplot(212)

    fig1.canvas.mpl_connect('figure_enter_event', enter_figure)
    fig1.canvas.mpl_connect('figure_leave_event', leave_figure)
    fig1.canvas.mpl_connect('axes_enter_event', enter_axes)
    fig1.canvas.mpl_connect('axes_leave_event', leave_axes)

    fig2 = plt.figure()
    fig2.suptitle('mouse hover over figure or axes to trigger events')
    ax1 = fig2.add_subplot(211)
    ax2 = fig2.add_subplot(212)

    fig2.canvas.mpl_connect('figure_enter_event', enter_figure)
    fig2.canvas.mpl_connect('figure_leave_event', leave_figure)
    fig2.canvas.mpl_connect('axes_enter_event', enter_axes)
    fig2.canvas.mpl_connect('axes_leave_event', leave_axes)

    plt.show()


def onpick(event):
    thisline = event.artist
    xdata = thisline.get_xdata()
    ydata = thisline.get_ydata()
    ind = event.ind
    points = tuple(zip(xdata[ind], ydata[ind]))
    print('onpick points:', points)


def click_on_points():
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title('click on points')
    line, = ax.plot(np.random.rand(100), 'o', picker=5)  # 5 points tolerance
    fig.canvas.mpl_connect('pick_event', onpick)
    plt.show()

# click_on_points()
mouse_hover_over_figure()