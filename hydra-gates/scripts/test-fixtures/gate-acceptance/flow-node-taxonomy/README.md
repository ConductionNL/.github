# gate-111 · flow-node-taxonomy

Three trees, one per verdict the gate can reach.

| Tree | Expect | Why |
| --- | --- | --- |
| `declares/` | rc 0 | every node in the directory declares its kind and category |
| `undeclared/` | rc 1, ONE `FAIL` line | `PlantedNode` declares nothing; `AlsoGoodNode` beside it must NOT be flagged, so the gate is shown to refuse a node rather than a directory |
| `no-nodes/` | rc 4 | no `lib/Service/Flow/Nodes` at all — NOT APPLICABLE, which is not a pass |

🔴 **The third tree is the one that matters most.** On a measured instance 38 of
65 step types are contributed by apps in other repositories, on their own
release cycles. A gate scoped by INTERFACE rather than by PATH would fire on
every one of them, in pull requests that cannot fix them.
