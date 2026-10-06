# Destination judgement task

Thank you for helping. This task takes about 30-45 minutes. Please work alone and do not discuss
the items with anyone involved in the project until you have returned the form.

## The setting

A mobile robot operates on one floor of a university building (corridor, laboratories, restrooms,
plants, windows). A person standing in the corridor gives the robot a short spoken request in
English. The robot can only drive to one of the 24 numbered **nodes** of its route map.

You receive:

- `map.png` - a plot of the floor: nodes (numbered), connections, and the fixed objects known to
  the robot;
- `environment_nodes.csv` - every node: number, name, coordinates (metres);
- `environment_objects.csv` - every fixed object known to the robot: identifier, class, the node
  it is attached to, coordinates;
- `items.csv` - 28 requests, each with a neutral code (Q01-Q28). The order is random.

Node and object labels are reproduced exactly from the historical configuration used at the time.
Judge each request using the map and tables as provided. If the available information appears
ambiguous, reflect that in the acceptable-node set, confidence, and optional comment.

## What to decide, for each request

Imagine you are a reasonable person who knows this floor exactly as the map shows it.

1. **Acceptable nodes.** Which node or nodes would be an acceptable place to take the person?
   List every node you consider acceptable (one or more), separated by `|`, e.g. `13|15|20`.
2. **Or: no node is appropriate.** If no node on the map is an acceptable answer, or the request
   is too unclear to act on, write `yes` in `no_node_appropriate` and leave `acceptable_nodes`
   empty. This is a legitimate answer, not a failure: it means the robot should ask for
   clarification instead of driving somewhere.
3. **Clearly wrong nodes (optional).** Nodes that would be a clear mistake, if any stand out.
4. **Confidence**: `high`, `medium` or `low`.
5. **Comment (optional)**: anything that made the item hard or ambiguous.

There are no trick items and no expected number of "no node" answers. Do not try to guess what
the robot did; you are not told, on purpose.

## Returning

Fill in `response_form.csv` (one row per code, all 28 rows) and send it back unchanged in name.
Do not edit the `code` or `request` columns. Every row needs a confidence (`high`, `medium` or `low`).

Before returning the form, please complete `evaluator.txt` (name, affiliation/role, date) and the
confirmation in it, and send both files back together.
