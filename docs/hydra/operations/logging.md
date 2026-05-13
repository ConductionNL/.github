# Logging

## Log files

Every `dev-run.sh` run writes a log to `logs/<stage>-<timestamp>.jsonl`:

```
logs/builder-20260402T133500Z.jsonl
logs/reviewer-20260402T140000Z.jsonl
logs/security-20260402T140000Z.jsonl
```

Timestamps are UTC. The `logs/` directory is gitignored.

## Log format

Output is JSONL (one JSON object per line, flushed immediately). This is produced by
Claude Code's `--output-format stream-json` flag. Key event types:

| `type` | Description |
|---|---|
| `system` | Init event — session ID, available tools, model |
| `assistant` | Agent response — text or tool use |
| `user` | Tool results returned to the agent |
| `result` | Final summary — `is_error`, `result`, `total_cost_usd`, `num_turns` |

## Parsing logs

Extract the final result from a log file:

```bash
python3 -c "
import json
for line in open('logs/builder-20260402T133500Z.jsonl'):
    try:
        d = json.loads(line)
        if d.get('type') == 'result':
            print('error:', d.get('is_error'))
            print('turns:', d.get('num_turns'))
            print('cost: $', d.get('total_cost_usd'))
            print(d.get('result', '')[:500])
    except: pass
"
```

## GitHub Actions / Kubernetes

In GitHub Actions, logs go to the workflow run output (stdout). In Kubernetes, logs are
captured by the container runtime and accessible via `kubectl logs`.
