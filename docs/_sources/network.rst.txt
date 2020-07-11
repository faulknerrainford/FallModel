########
Network
########

There are two versions of the network used in the current modelling. The first only features a single Intervention node.
The second features two intervention nodes.

The network centres around the Home node which has connections to and from the Hospital, GP, Social and Intervention
nodes and a connection to the Care node (which is a sink node). The other edges in the system mostly signify falls,
edges to GP from Interventions, Social and Home nodes are there for moderate falls. Likewise the same set of nodes have
edges to Hospital are for severe falls. The last edge from Hospital to Care is like the edge from Home to Care which is
for agents with mobility less than zero.

**************************************
Control and Parameter Setting Network
**************************************

.. image:: FallInterventionNetwork.png
  :width: 400
  :alt: Network of nodes, Home in the center with Hospital, GP, Intervention, Social and Care nodes around it. Edges run
        to and from all the nodes to home except Care which only have incoming edges from Home and Hospital and no
        outgoing edges. There are also edges from Intervention and Social to Hospital and GP.

*****************************
Other Specifications Network
*****************************

.. image:: FallInterventionOpenNetwork.png
  :width: 400
  :alt: Network of nodes, Home in the center with Hospital, GP, Intervention, Open Intervention, Social and Care nodes
        around it. Edges run to and from all the nodes to home except Care which only have incoming edges from Home and Hospital and no
        outgoing edges. There are also edges from Intervention, Open Intervention and Social to Hospital and GP.


****************
Node Algorithms
****************

There are many different functions performed in the nodes including perception filtering. We describe the main
algorithms used in individual nodes and fall nodes in general here.

------------
Fall Checks
------------
We use a random number and a normal distribution based on the agents mobility to check for falls. We scale the mean to
check for different sorts of falls.

.. math::
    f_{severe} = e^{-3m}\\
    f_{moderate}=e^{-3(0.9m)}\\
    f_{mild}=e^{-3(0.7m)}

Where :math:`m` is mobility. We sample from a uniform random distribution on the interval [0:1], :math:`r`, and starting with severe we check to see if :math:`r`
is less than :math:`f_{severe}`. If :math:`r` is less than the fall value then we dictate that that type of fall will occur.


------------------
Predicting Falls
------------------
To predict the next fall an agent is going to have we use a poisson distribution for each type of fall. We draw a sample
from each distribution, this sample is the time till the next fall of that type. The first type of fall to occur and the
time to it's occurrence is our fall prediction.

.. math::
    t_{severe} = Pois(-log(1-m))\\
    t_{moderate} = Pois(-log(1-0.9m))\\
    t_{mild} = Pois(-log(1-0.7m))\\
    t_{fall} = min(t_{severe}, t_{moderate}, t_{mild})


--------------------------
Node Perception Filtering
--------------------------
The standard node perception filtering for fall nodes is based on the edges and end nodes available and the properties
of the agent. There are 3 stages of Perception filtering:

1. Remove edges from Perception with\:
    a) wellbeing limits which the agent does not match
    b) referral requirement which the agent does not meet

2. If agent_mobility<0 and Care Node in Perception End Nodes:
    Perception = edge with Care end node

3. Perform fall check, if agent falls set agent_wellbeing to 'Fallen' and log fall, then\:
    a) if Severe fall: Perception = edge with Hospital end node
    b) if Moderate fall: Perception = edge with GP end node


----------------
Home Prediction
----------------
To calculate  how long the agent will stay at the Home node and possibly where it will go,
[queue time (relative to current time :math:`t_c`), destination, duration],  from there we perform the following algorithm:

+ Determine :math:`minimum\_energy` requirement for edges leaving Home node
+ If :math:`agent\_energy < minimum\_energy`:
    + :math:`recovery\_time = (minimum\_energy-agent\_energy)/recovery\_rate`
    + Predict fall on agent\_mobility to get fall_time and fall_type
    + :math:`t = 1`
    + :math:`m = agent\_mobility`
    + while :math:`t <` fall\_time:
        + :math:`m = m +` mobility\_change\\
        + [fall\_time\*, fall\_type\*] = Predict fall on m \\
        + if fall\_time\* < fall\_time:
            [fall\_time, fall\_type] = [fall\_time\*, fall\_type\*]
        + :math:`t = t + 1`
    + if fall\_time < recovery\_time:
        + log fall
        + set agent_wellbeing to 'Fallen'
        + if fall\_type == 'Severe':
            agent queues at [t_c + fall\_time, Hospital, fall\_time]
        + if fall\_type == 'Moderate':
            agent queues at [t_c + fall\_time, GP, fall\_time]
        + if fall\_type == 'Mild':
            agent queues at [t_c + recovery\_time, None, recovery\_time]
    + else:
        agent queues at [t_c + recovery\_time, None, recovery\_time]

+ Else:
    agent queues at [t_c+1, None, 1]



--------------------
Hospital Prediction
--------------------

We predict the time an agent will spend in hospital using a sample from a normal distribution. We set the mean such that
individuals with high mobility or high resources spend on average 5 days in hospital from a severe fall.

.. math::
    mean = -9 min(m, 1)+14

where :math:`m` is agent\_mobility

*****
Node
*****

.. automodule:: Fall_nodes
    :members:

*********
Balancer
*********

There are two forms of the balancer algorithm, the first used by parameter setting. Most of the existing system
specifications do not use network dynamics. The second is used by the dynamic specifications.

---------------------------
Parameter Setting Balancer
---------------------------

1. IntervalHistory : list of Intervals

2. :math:`c` := Intervention.Capacity

3. :math:`i` := current average Interval
4. IntervalHistory += :math:`[i]`
5. If Interval has increased since last week, and Interval > a week:
    Intervention.Capacity := :math:`c+1`
6. Else if Interval has decreased since last week, and Interval < a week:
    Intervention.Capacity := max:math:`(c-1,0)`

--------------------------
Dynamic Capacity Balancer
--------------------------

1. IntervalHistory : list of Intervals

2. :math:`c_c` := Intervention.Capacity

3. :math:`c_o` := OpenIntervention.Capacity

4. :math:`i` := current average Interval
5. IntervalHistory += :math:`[i]`
6. If Interval has increased since last week, and Interval > a week and :math:`c_o`>0:
    Intervention.Capacity := :math:`c_c+1`
    OpenIntervention.Capacity := :math:`c_o-1`
7. Else if Interval has decreased since last week, and Interval < a week and :math:`c_c`>0:
    Intervention.Capacity := :math:`c_c-1`
    OpenIntervention.Capacity := :math:`c_o+1`

--------------
Balancer Code
--------------

.. automodule:: Fall_Balancer
    :members:
