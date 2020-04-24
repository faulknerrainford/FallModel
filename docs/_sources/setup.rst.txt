Introduction
============

The FallModel package is a domain specific implementation of the SPmodelling framework:
https://faulknerrainford.github.io/SPmodelling/
Both packages are required to run the model. It is recommened that runs are done using a specification and the
SPModelling function SPm.py, see SPmodelling documentation for its usage.

It is an abstract model of care, social and medical systems surrounding those with declining mobility.

Installation
-------------
FallModel requires Python 3.6+ with a virtual environment, pip and neo4j.
It can be installed via pip:

.. code-block:: python

    pip install git+git:https://github.com/faulknerrainford/SPModelling
    pip install git+git:https://github.com/faulknerrainford/FallModel

You will also need an install of neo4j desktop: https://neo4j.com/download-neo4j-now/
The settings for the accounts on your graph will need to be given in the specification file.

Specification
--------------
The SPModelling framework module uses a specification.py file this defines the specific model being used. The
specification for FallModel must start with:

.. code-block:: python

    from FallModel import Fall_nodes as Nodes
    from FallModel import Fall_Monitor as Monitor
    from FallModel import Fall_Balancer as Balancer
    from FallModel import Fall_agent as Agents
    from FallModel import Fall_Population as Population
    from FallModel import Fall_reset_dynamic as Reset
    import sys

This connects the FallModel into the SPmodelling systems. The SPm function must be called from the same location as
the specification.py file using the imports.

.. code-block::

    specname = <name_of_this_specification>

It then defines the name for this specification, this particular network. It uses this in tagging output files.

.. code-block::

    """List of FallNodes used in system"""
    nodes = [Nodes.CareNode(), Nodes.HosNode(), Nodes.SocialNode(), Nodes.GPNode(), Nodes.InterventionNode(),
             Nodes.InterventionNode("InterventionOpen"), Nodes.HomeNode()]

The nodes used in the network are defines in terms of the FallModel nodes. These objects will be used to process the
agents flow for each node in the flow function.

.. code-block::

    savedirectory = <output_file_directory>

The output directory can be defined relative to the specification files location.

.. code-block::

    database_uri = "bolt://localhost:7687" # Set for a local neo4j database, change for remote databases

The location of the database is required, for local databases this should be as above.

.. code-block::

    """Account names and passwords for databases"""
    Flow_auth = ("Flow", "Flow")
    Balancer_auth = ("Balancer", "bal")
    Population_auth = ("Population", "pop")
    Structure_auth = ("Structure", "struct")
    Reset_auth = ("dancer", "dancer")
    Monitor_auth = ("monitor", "monitor")

Running
--------

Once the specification of the system exists the system can be run using SPmodelling.SPm, see SPmodelling documentation
for usage.