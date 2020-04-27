params = [0.8, 0.9, 1]


def countactiveagents(tx):
    """
    Utility function provides the number of agents in the database discounting those are the Care Node.

    :param tx: neo4j database read transaction

    :return: number of active agents in system
    """
    total_agents = tx.run("MATCH (n:Agent) ""WITH n ""RETURN count(*)").value()[0]
    care_agents = tx.run("MATCH (n:Agent)-[r:LOCATED]->(a:Node) ""WHERE a.name='Care' ""RETURN count(*)").value()[0]
    return total_agents - care_agents


def check(ses, ps):
    """
    confirms number of agents below designated population size. If population correct returns false

    :param ses: neo4j database session
    :param ps: int population size to be maintained

    :return: int number of agents below population size or false if population correct
    """
    active = ses.read_transaction(countactiveagents)
    if active < ps:
        for i in range(ps - active):
            return ps - active
    return False
