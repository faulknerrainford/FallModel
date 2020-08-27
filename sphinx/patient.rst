---------------------------------
Patient Physical Agent Algorithm
---------------------------------

1. Perception
    + Remove Edges where Agent.Energy < Edge.End_Node.Energy
2. Choose
    + Remove Edges where Edge.Mood > Agent.Mood
    + Select from remaining edges using a weighted sampling, we generate the weights as follows:
        +  For each edge we get the agent.inclination values corresponding to the edge.type
        +  We take the list of agent.inclination values and normalize them to give the sample weights
3. Payment
    + If Agent.Energy > Edge.Energy + Edge.End_node.Energy:
        + Deduct Edge.Energy from Agent.Energy
    + Else:
        + Search for carers
        + If a carer has sufficient energy take it
        + Else fail to move
    + Add Edge.Mobility_Modifier to Agent.Mobility
        + Update Agent.Wellbeing
            + If Agent.Mobility <= 0: Agent.Wellbeing = "Fallen"
            + Else If Agent.Mobility > 1: Agent.Wellbeing = "Healthy"
            + Else If Agent.Wellbeing == "Healthy": Agent.Wellbeing = "At Risk"
    + Add Edge.Mood_Modifier to Agent.Mood
4. Move
    + Delete Agents existing location edge
    + Create new edge from agent to Edge.End_Node for the selected Edge

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

------------------------------
Patient Social Agent Algorithm
------------------------------

1. Look
    + Agent checks its local physical environment for co-located agents
2. Update
    + Compares co-located agents and social contacts and updates last usage value for co-located contacts
3. Talk
    + Randomly check to see if a new social contact is forms with a co-located agent based on uniform random number being lower than the following equation based on m the length of the shortest undirected path between :math:`Agent_a` and :math:`Agent_b`
            + where :math:`m <= 6`: :math:`(Agent_a.social + Agent_b.social - 4)/24 + 1/(2m-2)`
            + where :math:`m > 6`: :math:`(Agent_a.social + Agent_b.social -4)/24`
4. Listen
    + If they have a new social contact who has a contact to a carer there is a .5 chance that :math:`Agent_a` also forms a social and care contact with that carer
5. React
    + Checks is agent has too many bonds, if it does:
        + If the length of :math:`Agent_a`'s list of carer contacts is greater than :math:`Agent_a.social`:
            + Drop all social contact with other agents
            + Drop most recently met carers until length is equal to :math:`Agent_a.social`
        + If the length of :math:`Agent_a`'s list of carer contact is equal to :math:`Agent_a.social`
            + Drop all social contact with other agents
        + Else
            + Drop social contacts with other agents created in the last 5 timesteps, starting with the most recent
            + Drop social contacts with the oldest last usage

------------
Patient Code
------------

.. autoclass:: Fall_agent.Patient
    :members: