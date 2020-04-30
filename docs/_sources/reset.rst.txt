Reset
=====
The Reset class is called by the SPm function to clear and initialise the database.
The SPm function clears the database, sets a clock and an output tag based on the Rest class being used and the current
specification. It then runs the Rest classes set_nodes, set_edges and generate_population functions in order.

.. autoclass:: Fall_reset.Reset
    :special-members:
    :members: