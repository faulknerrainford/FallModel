from statistics import mean
import logging
from SPmodelling import Balancer
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


def timesincedischarge(txl, intf):
    """
    Utility function reports the time between any hospital discharge and attending an intervention. Only recorded if
    both events occur.

    :param txl: neo4j database write transaction
    :param intf: Interface for database calls

    :return: list of times in integer timesteps
    """
    times = []
    agents = intf.getnodeagents(txl, "Intervention", "name")
    for agent in agents:
        log = parselog(agent["log"])
        log.reverse()
        lasthosdis = [entry for entry in log if entry[0] == "Hos discharge"]
        if lasthosdis:
            lasthosdis = lasthosdis[0]
            times = times + [intf.gettime(txl) - lasthosdis[1]]
    return times


def adjustcapasity(txl, intf, history, dynamic=True):
    """
    Rule function that applies the capacity change algorithm in the  case of two intervention node systems. This is uses
    a history variable that is cleared when the capacity is adjusted so that another five timesteps must pass before the
    capacity can be changed again. This only modifies OpenIntervention if dynamic is true else only intervention is
    modified.

    :param txl: neo4j database write transaction
    :param intf: Interface for database calls
    :param history: List of previous average times since discharge

    :return: history
    """
    currenttimes = timesincedischarge(txl, intf)
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
                if intf.getnodevalue(txl, "InterventionOpen", "cap", uid="name") > 0 and dynamic:
                    intf.updatenode(txl, "Intervention", "cap", intf.getnodevalue(txl, "Intervention", "cap", uid="name")
                                + 1, "name")
                    intf.updatenode(txl, "InterventionOpen", "cap", intf.getnodevalue(txl, "InterventionOpen", "cap",
                                                                                  uid="name") - 1, "name")
            else:
                    intf.updatenode(txl, "Intervention", "cap", intf.getnodevalue(txl, "Intervention", "cap", uid="name")
                                + 1, "name")
            return []
        elif history[-5] - history[-1] > 0 and history[-1] < 5:
            if intf.getnodevalue(txl, "Intervention", "cap", uid="name") > 0:
                intf.updatenode(txl, "Intervention", "cap", intf.getnodevalue(txl, "Intervention", "cap", uid="name")
                                - 1, "name")
                if dynamic:
                    intf.updatenode(txl, "InterventionOpen", "cap", intf.getnodevalue(txl, "InterventionOpen", "cap",
                                                                                      uid="name") + 1, "name")

            return []
        else:
            return history


class FlowReaction(Balancer.FlowReaction):
    """
    Fall specific implementation of a Balancer for adjusting network values. Applies the adjust capacity rule.
    """

    def __init__(self, uri=None, author=None):
        super(FlowReaction, self).__init__(uri, author)
        self.storage = []

    def applyrules(self, txl, intf):
        """
        Applies the adjust capacity rule

        :param txl: neo4j database write transaction
        :param intf: Interface for database calls

        :return: None
        """
        self.storage = adjustcapasity(txl, intf, self.storage, specification.dynamic)
