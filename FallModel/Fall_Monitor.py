from matplotlib import pylab as pylab
import pickle
import numpy as np
from matplotlib import pyplot as plt
from FallModel.Fall_Balancer import timesincedischarge
import SPmodelling.Interface as intf
from statistics import mean
from SPmodelling.Monitor import Monitor as SPMonitor
import specification


class MassMonitor(SPMonitor):
    """
    Monitor class extends SPModelling Monitor. It is intended to monitor the database of the model and report and store
    summary statistics to enable later analysis. It records system interval, intervention interval, capacity of the
    first intervention node, average number of each fall type before care. It returns a record of these in the raw data
    and in the form of a graph. It also saves out the logs for all the agents in the system at the end of its run.
    """

    def __init__(self):
        """
        Sets up four graph grid for monitoring system.
        """
        super(Monitor, self).__init__(show_local=False)
        self.nrecord = None
        self.fig.suptitle("Network Stats over Time")
        # Set up subplots with titles and axes
        self.xlims = (0, 20)
        self.ylims = (0, 12)
        self.ax1 = plt.subplot2grid((2, 2), (0, 0))
        self.ax2 = plt.subplot2grid((2, 2), (0, 1))
        self.ax3 = plt.subplot2grid((2, 2), (1, 0))
        self.ax4 = plt.subplot2grid((2, 2), (1, 1))
        self.ax1.set_title('Average falls in lifetime')
        self.ax1.set_ylabel("No. Falls")
        self.ax1.set_xlabel("Time")
        self.ax1.set_ylim(self.ylims)
        self.ax1.set_xlim(self.xlims)
        self.ax2.set_title('Intervention Interval')
        self.ax2.set_ylabel("Interval")
        self.ax2.set_xlabel("Time")
        self.ax2.set_ylim(self.ylims)
        self.ax2.set_xlim(self.xlims)
        self.ax3.set_title('System Interval')
        self.ax3.set_ylabel("Interval")
        self.ax3.set_xlabel("Time")
        self.ax3.set_ylim(self.ylims)
        self.ax3.set_xlim(self.xlims)
        self.ax4.set_title('Population Distribution')
        self.ax4.set_ylabel("Proportion")
        self.ax4.set_xlabel("Time")
        self.ax4.set_ylim(self.ylims)
        self.ax4.set_xlim(self.xlims)
        # Set data for plot 1
        self.y11 = np.zeros(0)
        self.y12 = np.zeros(0)
        self.y13 = np.zeros(0)
        self.y2 = np.zeros(0)
        self.y3 = np.zeros(0)
        self.y41 = np.zeros(0)
        self.y42 = np.zeros(0)
        self.y43 = np.zeros(0)
        self.p11, = self.ax1.plot(self.t, self.y11, 'b-', label="Mild")
        self.p12, = self.ax1.plot(self.t, self.y12, 'g-', label="Moderate")
        self.p13, = self.ax1.plot(self.t, self.y13, 'm-', label="Severe")
        self.ax1.legend([self.p11, self.p12, self.p13], [self.p11.get_label(),
                                                         self.p12.get_label(), self.p13.get_label()])
        self.p2, = self.ax2.plot(self.t, self.y2, 'm-')
        self.p3, = self.ax3.plot(self.t, self.y3, 'g-')
        self.p41, = self.ax4.plot(self.t, self.y41, 'b-', label="Healthy")
        self.p42, = self.ax4.plot(self.t, self.y42, 'g-', label="At Risk")
        self.p43, = self.ax4.plot(self.t, self.y43, 'm-', label="Fallen")
        self.ax4.legend([self.p41, self.p42, self.p43], [self.p41.get_label(),
                                                         self.p42.get_label(), self.p43.get_label()])
        self.xmin = 0.0
        self.xmax = 20.0
        self.ymin1 = 0.0
        self.ymax1 = 12.0
        self.y = 0
        self.y4 = 0
        self.y1 = 0
        self.x = 0
        self.y3storage = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]

    def snapshot(self, dri, ctime):
        """
        Captures the current statistics of the system and updates graph grid, including average system interval,
        intervention interval, average number of falls at end of system interval and proportions of population in each
        population category.

        :param dri: neo4j database driver
        :param ctime: current timestep

        :return: None
        """
        look = dri.run("MATCH (n:Node) "
                       "WHERE n.name = {node} "
                       "RETURN n", node="Intervention")
        self.nrecord = look.values()
        if super(Monitor, self).snapshot(dri, ctime):
            # Update plot 1 - Int Cap
            # Update to track average number of each type of fall for people in care.
            ses = dri.session()
            [mild, moderate, severe, agents_n] = ses.run("MATCH (n:Node) "
                                                         "WHERE n.name={node} "
                                                         "RETURN n.mild, n.moderate, n.severe, n.agents",
                                                         node="Care").values()[0]
            ses.close()
            if agents_n:
                self.y11 = pylab.append(self.y11, mild / agents_n)
                self.p11.set_data(self.t, self.y11)
                self.y12 = pylab.append(self.y12, moderate / agents_n)
                self.p12.set_data(self.t, self.y12)
                self.y13 = pylab.append(self.y13, severe / agents_n)
                self.p13.set_data(self.t, self.y13)
                if max([mild / agents_n, moderate / agents_n, severe / agents_n]) > self.y1:
                    self.y1 = max([mild / agents_n, moderate / agents_n, severe / agents_n])
                    self.p11.axes.set_ylim(0.0, self.y1 + 1.0)
                    self.p12.axes.set_ylim(0.0, self.y1 + 1.0)
                    self.p13.axes.set_ylim(0.0, self.y1 + 1.0)
            else:
                self.y11 = pylab.append(self.y11, 0)
                self.p11.set_data(self.t, self.y11)
                self.y12 = pylab.append(self.y12, 0)
                self.p12.set_data(self.t, self.y12)
                self.y13 = pylab.append(self.y13, 0)
                self.p13.set_data(self.t, self.y13)
            # Update plot 2 - Hos to Int
            gaps = timesincedischarge(dri)
            if gaps:
                hiint = mean(timesincedischarge(dri))
                self.y3storage = self.y3storage + [hiint]
                if len(self.y3storage) >= 10:
                    self.y3storage = self.y3storage[-10:]
            if self.y3storage:
                self.y2 = pylab.append(self.y2, mean(self.y3storage))
                if self.y < mean(self.y3storage):
                    self.y = mean(self.y3storage)
                self.p2.set_data(self.t, self.y2)
            # Update plot 3 - Start to Care
            careint = intf.getnodevalue(dri, "Care", "interval", uid="name")
            if careint:
                scint = careint
            else:
                scint = 0
            self.y3 = pylab.append(self.y3, scint)
            if self.y < scint:
                self.y = scint
            self.p3.set_data(self.t, self.y3)
            # Update plot 4
            # Update plot showing distribution of well being in the general population.
            ses = dri.session()
            wb = ses.run("MATCH (a:Agent)-[r:LOCATED]->(n:Node) "
                         "WHERE NOT n.name={node} "
                         "RETURN a.wellbeing",
                         node="Care").values()
            ses.close()
            wb = [val[0] for val in wb]
            healthy = wb.count("Healthy") / len(wb)
            at_risk = wb.count("At risk") / len(wb)
            fallen = wb.count("Fallen") / len(wb)
            self.y41 = pylab.append(self.y41, healthy)
            self.p41.set_data(self.t, self.y41)
            self.y42 = pylab.append(self.y42, at_risk)
            self.p42.set_data(self.t, self.y42)
            self.y43 = pylab.append(self.y43, fallen)
            self.p43.set_data(self.t, self.y43)
            if max([healthy, at_risk, fallen]) / len(wb) > self.y4:
                self.y4 = max([healthy, at_risk, fallen])
                self.p41.axes.set_ylim(0.0, self.y4 + 1.0)
                self.p42.axes.set_ylim(0.0, self.y4 + 1.0)
                self.p43.axes.set_ylim(0.0, self.y4 + 1.0)
            # Update plot axes
            if self.x >= self.xmax - 1.00:
                self.p11.axes.set_xlim(0.0, self.x + 1.0)
                self.p12.axes.set_xlim(0.0, self.x + 1.0)
                self.p13.axes.set_xlim(0.0, self.x + 1.0)
                self.p2.axes.set_xlim(0.0, self.x + 1.0)
                self.p3.axes.set_xlim(0.0, self.x + 1.0)
                self.p41.axes.set_xlim(0.0, self.x + 1.0)
                self.p42.axes.set_xlim(0.0, self.x + 1.0)
                self.p43.axes.set_xlim(0.0, self.x + 1.0)
                self.xmax = self.x
            if self.y > self.ymax1 - 1.0:
                self.p2.axes.set_ylim(0.0, self.y + 1.0)
                self.p3.axes.set_ylim(0.0, self.y + 1.0)
            if self.show:
                plt.pause(0.0005)

    def close(self, dri):
        """
        Saves figure, figure data, logs of agents in system at end of run to the output directory given in Specification
        with name tag given in database.

        :param dri: neo4j database driver

        :return: None
        """
        super(Monitor, self).close(dri)
        runname = intf.getrunname(dri)
        print(self.clock)
        ses = dri.session()
        logs = ses.run("MATCH (a:Agent) RETURN a.log").values()
        ses.close()
        pickle_lout = open(specification.savedirectory + "logs_" + runname + ".p", "wb")
        pickle.dump(logs, pickle_lout)
        pickle_lout.close()
        pickle_out = open(specification.savedirectory + "records_" + runname + ".p", "wb")
        pickle.dump(self.records, pickle_out)
        pickle_out.close()
        pickle_gout = open(specification.savedirectory + "graphdata_" + runname + ".p", "wb")
        pickle.dump([self.y11, self.y12, self.y13, self.y2, self.y3, self.y41, self.y42, self.y43, self.t], pickle_gout)
        pickle_gout.close()
        # dump graph data as strings back into the database
        # save out graph
        plt.savefig("../FallData/figure_" + runname + "")
        if self.show:
            plt.show()
