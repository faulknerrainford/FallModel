#######
Agents
#######
Agents act using 5 step algorithm established in SPmodelling's agents. Each stage is broken down below. The Agent recieves
an already filtered perception from the node which is fed into step 1.

---------------------
Fall Agent Algorithm
---------------------

1. Perception
    + Remove Edges where Agent.Energy < Edge.Energy + Edge.End_Node.Energy
2. Choose
    + Remove Edges where Edge.Mood > Agent.Mood
    + Select from remaining edges using a weighted sampling, we generate the weights as follows:
        +  For each edge we get the agent.inclination values corresponding to the edge.type
        +  We take the list of agent.inclination values and normalize them to give the sample weights
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
    + Add Edge.Mood_Modifier to Agent.Mood
5. Learning
    + Deduct Edge.End_Node.Energy from Agent.Energy
    + Add Edge.End_Node.Mobility_Modifier to Agent.Mobility
        + Update Agent.Wellbeing
            + If Agent.Mobility <= 0: Agent.Wellbeing = "Fallen"
            + Else If Agent.Mobility > 1: Agent.Wellbeing = "Healthy"
            + Else If Agent.Wellbeing == "Healthy": Agent.Wellbeing = "At Risk"
    + Add Edge.End_Node.Mood to Agent.Mood
    + Add Edge.End_Node.Energy to Agent.Energy
    + If new Agent.Energy > Agent.Energy before move:
        Increment Agent.Inclination.Edge.type
    + Else if new Agent.Energy < Agent.Energy before move:
        Decrement Agent.Inclination.Edge.type
    + If Agent.Energy > 0.8:
        Increment Agent.Inclination.social
    + Else if Agent.Energy < 0.2:
        Increment Agent.Inclination.inactivity
    + If Agent.Mood > 0.8:
        Increment Agent.Inclination.social
        Decrement Agent.Inclination.inactivity
    + Else if Agent.Mood < 0.2:
        Decrement Agent.Inclination.social
        Increment Agent.Inclination.inactivity
    + If Agent.Mobility < 0.4:
        Increment Agent.Inclination.medical
        Increment Agent.Inclination.inactivity
    + Else if Agent.Mobility > 0.8:
        Decrement Agent.Inclination.inactivity
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

.. autoclass:: Fall_agent.Patient
    :members:

-----------
Population
-----------

.. automodule:: Fall_Population
    :members:
