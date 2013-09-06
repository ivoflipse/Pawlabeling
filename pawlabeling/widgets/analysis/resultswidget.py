from PySide import QtGui
from pubsub import pub
from pawlabeling.widgets.analysis import forceviewwidget, twodimviewwidget, pressureviewwidget, copviewwidget


class ResultsWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(ResultsWidget, self).__init__(parent)

        self.two_dim_view_widget = twodimviewwidget.TwoDimViewWidget(self)
        self.pressure_view_widget = pressureviewwidget.PressureViewWidget(self)
        self.force_view_widget = forceviewwidget.ForceViewWidget(self)
        self.cop_view_widget = copviewwidget.CopViewWidget(self)

        self.widgets = [self.two_dim_view_widget,
                        self.pressure_view_widget,
                        self.force_view_widget,
                        self.cop_view_widget]

        self.frame = -1

        self.tab_widget = QtGui.QTabWidget(self)
        self.tab_widget.addTab(self.two_dim_view_widget, "2D view")
        self.tab_widget.addTab(self.pressure_view_widget, "Pressure")
        self.tab_widget.addTab(self.force_view_widget, "Force")
        self.tab_widget.addTab(self.cop_view_widget, "COP")

        self.tab_widget.currentChanged.connect(self.update_active_widget)
        # Notify the first tab that its active
        pub.sendMessage("active_widget", widget=self.widgets[0])

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def update_widgets(self, contact_labels, contact_data, average_data):
        self.contact_labels = contact_labels
        self.contact_data = contact_data
        self.average_data = average_data
        self.update_active_widget()

    def update_active_widget(self):
        current_tab = self.tab_widget.currentIndex()
        widget = self.widgets[current_tab]
        # Tell the user we're calculating some results
        pub.sendMessage("update_statusbar", status="Switching results to {}".format(widget.label.text()))
        pub.sendMessage("active_widget", widget=widget)
