from statistics import mean
import logging
from SPmodelling.Balancer import Balancer as Balancer
import SPmodelling.Interface as intf
import specification


def parselog(log):
    """
    Utility function, parses log strings from agents and converts them to a list of tuples.

    :param log: string log format: "(<event>, <timestep>),..."

    :return: list of tuples [(<event>, <timestep>),...]
    """
    logging.debug(log)
    while isinstance(log, list):
        log = log[0]
    log = log.split("), (")
    log[0] = log[0].replace("(", "")
    log[-1] = log[-1].replace(")", "")
    log = [entry.split(",") for entry in log]
    log = [(entry[0], int(entry[1])) for entry in log]
    return log


def timesincedischarge(dri):
    """
    Utility function reports the time between any hospital discharge and attending an intervention. Only recorded if
    both events occur.

    :param dri: neo4j database driver

    :return: list of times in integer timesteps
    """
    times = []
    agents = intf.get_node_agents(dri, ["Intervention", "Node", "name"], "name")
    for agent in agents:
        log = parselog(agent["log"])
        log.reverse()
        lasthosdis = [entry for entry in log if entry[0] == "Hos discharge"]
        if lasthosdis:
            lasthosdis = lasthosdis[0]
            times = times + [intf.gettime(dri) - lasthosdis[1]]
    return times


def adjustcapasity(dri, history, dynamic=True):
    """
    Rule function that applies the capacity change algorithm in the  case of two intervention node systems. This is uses
    a history variable that is cleared when the capacity is adjusted so that another five timesteps must pass before the
    capacity can be changed again. This only modifies OpenIntervention if dynamic is true else only intervention is
    modified.

    :param dri: neo4j database driver
    :param history: List of previous average times since discharge
    :param dynamic: indicates if adjustment to OpenIntervention is needed

    :return: history
    """
    currenttimes = timesincedischarge(dri)
    if not currenttimes and history:
        currentav = history[-1]
    elif not currenttimes:
        currentav = 14
    else:
        currentav = mean(currenttimes)
    history = history + [currentav]
    # If it has been less than 20 time steps since last change do nothing
    if len(history) < 20:
        return history
    else:
        if history[-5] - history[-1] < -1 and history[-1] > 5:
            if dynamic:
                if intf.get_node_value(dri, ["InterventionOpen", "Node", "name"], "cap") > 0 and dynamic:
                    intf.update_node(dri, ["Intervention", "Node", "name"], "cap",
                                     intf.get_node_value(dri, ["Intervention", "Node", "name"], "cap")
                                     + 1, "name")
                    intf.update_node(dri, ["InterventionOpen", "Node", "name"], "cap",
                                     intf.get_node_value(dri, "InterventionOpen", "cap",
                                                         ) - 1, "name")
            else:
                intf.update_node(dri, ["Intervention", "Node", "name"], "cap",
                                 intf.get_node_value(dri, ["Intervention", "Node", "name"], "cap")
                                 + 1, "name")
            return []
        elif history[-5] - history[-1] > 0 and history[-1] < 5:
            if intf.get_node_value(dri, ["Intervention", "Node", "name"], "cap", uid="name") > 0:
                intf.update_node(dri, ["Intervention", "Node", "name"], "cap",
                                 intf.get_node_value(dri, ["Intervention", "Node", "name"], "cap", uid="name")
                                 - 1, "name")
                if dynamic:
                    intf.update_node(dri, ["InterventionOpen", "Node", "name"], "cap",
                                     intf.get_node_value(dri, ["InterventionOpen", "Node", "name"], "cap",
                                                         ) + 1, "name")

            return []
        else:
            return history


class FlowReaction(Balancer):
    """
    Fall specific implementation of a Balancer for adjusting network values. Applies the adjust capacity rule.
    """

    def __init__(self):
        super(FlowReaction, self).__init__()
        self.storage = []

    def apply_change(self, dri):
        """
        Applies the adjust capacity rule

        :param dri: neo4j database driver

        :return: None
        """
        self.storage = adjustcapasity(dri, self.storage, specification.dynamic)
