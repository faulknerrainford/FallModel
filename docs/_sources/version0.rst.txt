######################
Version 0 Algorithms
######################

This contains the algorithms used in the version 0 classes of the system. These are relevant to replication of results
found in the original 2020 ALife SPmodelling paper.  These algorithms are preserved here for reference, the
documentation for the version 0 class and functions in the main body of documentation. Older version classes are marked
as <class>V<version number>.

---------------------
Fall Agent Algorithm
---------------------

1. Perception
    + Remove Edges where Agent.Energy < Edge.Energy + Edge.End_Node.Energy
2. Choose
    + Remove Edges where Node.Effort > Edge.Mobility*(Agent.Mobility + Agent.Confidence*Agent.Mobility_Resources) + Edge.Confidence(Agent.Confidence + Agent.Mobility*Agent.Confidence_Resources)
    + Select Edge with max(Edge.worth)
3. Move
    + Delete Agents existing location edge
    + Create new edge from agent to Edge.End_Node for the selected Edge
4. Payment
    + Deduct Edge.Energy from Agent.Energy
    + Add Edge.Mobility_Modifier to Agent.Mobility
        + Update Agent.Wellbeing
            + If Agent.Mobility <= 0: Agent.Wellbeing = "Fallen"
            + Else If Agent.Mobility > 1: Agent.Wellbeing = "Healthy"
            + Else If Agent.Wellbeing == "Healthy": Agent.Wellbeing = "At Risk"
    + Add Edge.Confidence_Modifier to Agent.Confidence
5. Learning
    + Deduct Edge.End_Node.Energy from Agent.Energy
    + Add Edge.End_Node.Mobility_Modifier to Agent.Mobility
        + Update Agent.Wellbeing
            + If Agent.Mobility <= 0: Agent.Wellbeing = "Fallen"
            + Else If Agent.Mobility > 1: Agent.Wellbeing = "Healthy"
            + Else If Agent.Wellbeing == "Healthy": Agent.Wellbeing = "At Risk"
    + Add Edge.End_Node.Confidence to Agent.Confidence
    + Add Edge.End_Node.Confidence_Resources to Agent.Confidence_Resources
    + Add Edge.End_Node.Mobility_Resources to Agent.Mobility_Resources
    + If Edge.End_Node is Care node:
        Log Agent entering Care
    + If Edge.End_Node has a capacity:
        Add 1 to Edge.End_Node.Load
    + If Agent has left Hospital:
        Log Agent being Discharged

6. Prediction*
    + If Edge.End_Node has Queue:
        Run Agent prediction at new node

-----------
Agent Code
-----------

.. autoclass:: Fall_agent.FallAgent
    :members: