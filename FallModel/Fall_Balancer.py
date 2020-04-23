from statistics import mean
import logging
from SPmodelling import Balancer


def parselog(log):
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


def adjustcapasity(txl, intf, history):
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
            if intf.getnodevalue(txl, "InterventionOpen", "cap", uid="name") > 0:
                intf.updatenode(txl, "Intervention", "cap", intf.getnodevalue(txl, "Intervention", "cap", uid="name")
                                + 1, "name")
                intf.updatenode(txl, "InterventionOpen", "cap", intf.getnodevalue(txl, "InterventionOpen", "cap",
                                                                                  uid="name") - 1, "name")
            return []
        elif history[-5] - history[-1] > 0 and history[-1] < 5:
            if intf.getnodevalue(txl, "Intervention", "cap", uid="name") > 0:
                intf.updatenode(txl, "Intervention", "cap", intf.getnodevalue(txl, "Intervention", "cap", uid="name")
                                - 1, "name")
                intf.updatenode(txl, "InterventionOpen", "cap", intf.getnodevalue(txl, "InterventionOpen", "cap",
                                                                                  uid="name") + 1, "name")
            return []
        else:
            return history


class FlowReaction(Balancer.FlowReaction):

    def __init__(self, uri=None, author=None):
        super(FlowReaction, self).__init__(uri, author)
        self.storage = []

    def applyrules(self, txl, intf):
        self.storage = adjustcapasity(txl, intf, self.storage)
