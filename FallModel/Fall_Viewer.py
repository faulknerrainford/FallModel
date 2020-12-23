from SPmodelling.Monitor import Monitor
from SPmodelling import Interface as intf
import numpy as np
import pandas as pd
import json


class OpinionViewer(Monitor):

    def __init__(self, dri):
        # Get list of agents in systems
        agents = intf.get_agents(dri)
        agents = [ag[0] for ag in agents]
        # Set up panel
        self.panel = [(ag, 'Agent', 'id') for ag in np.random.choice(agents, 50, False)]
        # Get initial values
        agents = [(ag, 'Agent', 'id') for ag in agents]
        opinions = [(ag, intf.get_node_value(dri, ag, 'opinion')) for ag in agents]
        truth = [op[1] for op in opinions]
        panel_sample = [ag for ag in self.panel if self.panel.index(ag) in np.random.choice(len(self.panel), 30, False)]
        panel = [op[1] for op in opinions if op[0] in panel_sample]
        survey = np.random.choice(truth, 30, False)
        # If clusters have not been formed in system wait until they have
        while True:
            try:
                groups = intf.clusters_in_system(dri)
                groups = [(cluster, 'Cluster', 'id') for cluster in groups]
                break
            except TypeError:
                pass
        groups = [intf.get_node_value(dri, cluster, 'opinion') for cluster in groups]
        # Set up pandas data frame
        time = intf.get_time(dri)
        d = {'Truth': [0], 'Survey': [0], 'Panel': [0],
             'Groups': [0], 'Time': [time]}
        self.df = pd.DataFrame(d, index=[0])
        for col in d.keys():
            self.df[col] = self.df[col].astype('object')
        self.df.at[time, 'Truth'] = truth
        self.df.at[time, 'Panel'] = panel
        self.df.at[time, 'Survey'] = survey
        self.df.at[time, 'Groups'] = groups
        # TODO: Call real time graph if in use

    def snapshot(self, dri, ctime):
        # Get opinions of all agents (with agent id)
        agents = [ag[0] for ag in intf.get_agents(dri)]
        agents = [(ag, 'Agent', 'id') for ag in agents]
        opinions = [(ag, intf.get_node_value(dri, ag, 'opinion')) for ag in agents]
        truth = [op[1] for op in opinions]
        # Sample opinions
        survey = np.random.choice(truth, 30, False)
        # sample panel opinions
        panel = []
        for ag in self.panel:
            op = intf.get_node_value(dri, ag, 'opinion')
            if not op and op != 0:
                self.panel.remove(ag)
            else:
                panel.append(op)
        while len(self.panel) < 40:
            sample = np.random.choice([ag[0] for ag in agents], 15, False)
            sample = [(ag, 'Agent', 'id') for ag in sample]
            print("check panel")
            print(len(self.panel))
            for ag in sample:
                if ag not in self.panel:
                    self.panel.append(ag)
        panel = np.random.choice(panel, 30, False)
        # Get opinions of groups
        groups = intf.clusters_in_system(dri)
        groups = [(cluster, 'Cluster', 'id') for cluster in groups]
        groups = [intf.get_node_value(dri, cluster, 'opinion') for cluster in groups]
        # Store all data sets in data frame
        time = intf.get_time(dri)
        self.df.at[time, 'Truth'] = truth
        self.df.at[time, 'Panel'] = panel
        self.df.at[time, 'Survey'] = survey
        self.df.at[time, 'Groups'] = groups
        self.df.at[time, 'Time'] = time
        # TODO: Call update to live graph

    def monitor_close(self, dri):
        super(OpinionViewer, self).monitor_close(dri)
        # Save data frame
        self.df.to_json(intf.get_run_name(dri)+'_ViewerData')
        # TODO: Save graph
