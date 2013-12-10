from PySide import QtGui
from pubsub import pub
from ...widgets.analysis import forceviewwidget, twodimviewwidget, pressureviewwidget, copviewwidget, gaitdiagramwidget
from ...models.model import model

class ResultsWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(ResultsWidget, self).__init__(parent)

        self.parent = parent
        self.model = model
        self.two_dim_view_widget = twodimviewwidget.TwoDimViewWidget(self)
        self.pressure_view_widget = pressureviewwidget.PressureViewWidget(self)
        self.force_view_widget = forceviewwidget.ForceViewWidget(self)
        self.cop_view_widget = copviewwidget.CopViewWidget(self)
        self.gait_diagram_widget = gaitdiagramwidget.GaitDiagramWidget(self)

        self.widgets = [self.two_dim_view_widget,
                        self.pressure_view_widget,
                        self.force_view_widget,
                        self.cop_view_widget,
                        self.gait_diagram_widget]

        self.current_widget = self.widgets[0]

        self.frame = -1

        self.tab_widget = QtGui.QTabWidget(self)
        self.tab_widget.addTab(self.two_dim_view_widget, "2D view")
        self.tab_widget.addTab(self.pressure_view_widget, "Pressure")
        self.tab_widget.addTab(self.force_view_widget, "Force")
        self.tab_widget.addTab(self.cop_view_widget, "COP")
        self.tab_widget.addTab(self.gait_diagram_widget, "Gait Diagram")
        self.tab_widget.currentChanged.connect(self.update_active_widget)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

        self.two_dim_view_widget.active = True

    def update_active_widget(self):
        self.current_tab = self.tab_widget.currentIndex()
        self.current_widget = self.widgets[self.current_tab]
        self.parent.set_max_length()

        # Tell the user we're calculating some results
        pub.sendMessage("update_statusbar", status="Switching results to {}".format(self.current_widget.label.text()))
        pub.sendMessage("active_widget", widget=self.current_widget)
