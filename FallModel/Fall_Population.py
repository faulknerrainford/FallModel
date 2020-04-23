params = [0.8, 0.9, 1]


def countactiveagents(tx):
    total_agents = tx.run("MATCH (n:Agent) ""WITH n ""RETURN count(*)").value()[0]
    care_agents = tx.run("MATCH (n:Agent)-[r:LOCATED]->(a:Node) ""WHERE a.name='Care' ""RETURN count(*)").value()[0]
    return total_agents - care_agents


def check(ses, ps):
    active = ses.read_transaction(countactiveagents)
    if active < ps:
        for i in range(ps - active):
            return ps - active
    return False
