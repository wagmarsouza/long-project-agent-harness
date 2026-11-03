"""VeriMission 8.1 projections, explicit run imports, and cost accounting."""
from datetime import datetime
import json
import math
from pathlib import Path
import subprocess


AGENTS = ("codex", "opencode", "claude", "hermes")
COST_STATES = ("actual", "estimated", "unpriced")
RUN_STATES = ("completed", "failed", "interrupted", "unknown")


def extend(Base, require, digest, now, file_digest, nonempty, Refusal):
    class Harness81(Base):
        @staticmethod
        def _iso(value, field, optional=False):
            if optional and value is None:
                return None
            require(nonempty(value), "RUN_TIME", field + " must be an ISO-8601 timestamp")
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise Refusal("RUN_TIME", field + " must be an ISO-8601 timestamp")

        @staticmethod
        def _projection_nodes(state):
            nodes = [{"id": "mission:current", "kind": "mission", "label": state["mission"]["objective"], "status": "current"}]
            edges = []
            for row in state["mission"].get("requirements", []):
                rid = "requirement:" + row["id"]
                nodes.append({"id": rid, "kind": "requirement", "label": row["id"] + ": " + row["description"], "status": "declared"})
                edges.append({"from": "mission:current", "to": rid, "kind": "contains"})
                for criterion in row["criteria"]:
                    edges.append({"from": rid, "to": "criterion:" + criterion, "kind": "requires"})
            for row in state["mission"]["criteria"]:
                cid = "criterion:" + row["id"]
                nodes.append({"id": cid, "kind": "criterion", "label": row["id"] + ": " + row["description"], "status": "declared"})
                edges.append({"from": "mission:current", "to": cid, "kind": "accepts_by"})
            for row in state.get("tasks", {}).values():
                tid = "task:" + row["id"]
                nodes.append({"id": tid, "kind": "task", "label": row["id"] + ": " + row["title"], "status": row["status"]})
                edges.append({"from": "mission:current", "to": tid, "kind": "plans"})
                edges.extend({"from": tid, "to": "criterion:" + cid, "kind": "covers"} for cid in row["criteria"])
                edges.extend({"from": tid, "to": "task:" + dep, "kind": "depends_on"} for dep in row.get("depends_on", []))
                edges.extend({"from": tid, "to": "claim:" + claim, "kind": "relies_on"} for claim in row.get("relies_on", []))
            for row in state["cycles"]:
                cid = "cycle:" + str(row["id"])
                nodes.append({"id": cid, "kind": "cycle", "label": "Cycle " + str(row["id"]), "status": row["status"]})
                edges.append({"from": cid, "to": "task:" + row["task"], "kind": "executes"})
                edges.extend({"from": cid, "to": "criterion:" + criterion, "kind": "checks"} for criterion in row["criteria"])
            for row in state["claims"].values():
                cid = "claim:" + row["id"]
                nodes.append({"id": cid, "kind": "claim", "label": row["id"] + ": " + row["statement"], "status": row["status"]})
                edges.append({"from": cid, "to": "cycle:" + str(row["cycle"]), "kind": "supported_by"})
                edges.extend({"from": cid, "to": "claim:" + dep, "kind": "depends_on"} for dep in row.get("depends_on", []))
            return sorted(nodes, key=lambda row: row["id"]), sorted(edges, key=lambda row: (row["from"], row["to"], row["kind"]))

        @staticmethod
        def _graph_text(payload, format_name):
            lookup = {row["id"]: "n" + str(i) for i, row in enumerate(payload["nodes"])}
            if format_name == "mermaid":
                lines = ["%% VeriMission projection; source revision " + str(payload["source"]["state_revision"]), "flowchart LR"]
                for row in payload["nodes"]:
                    label = (row["kind"] + " | " + row["label"] + " | " + row["status"]).replace('"', "'").replace("\n", " ")
                    lines.append("  " + lookup[row["id"]] + '["' + label + '"]')
                for row in payload["edges"]:
                    if row["from"] in lookup and row["to"] in lookup:
                        lines.append("  " + lookup[row["from"]] + " -->|" + row["kind"] + "| " + lookup[row["to"]])
                return "\n".join(lines) + "\n"
            lines = ["// VeriMission projection; source revision " + str(payload["source"]["state_revision"]), "digraph verimission {"]
            for row in payload["nodes"]:
                label = (row["kind"] + " | " + row["label"] + " | " + row["status"]).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
                lines.append("  " + lookup[row["id"]] + ' [label="' + label + '"];')
            for row in payload["edges"]:
                if row["from"] in lookup and row["to"] in lookup:
                    lines.append("  " + lookup[row["from"]] + " -> " + lookup[row["to"]] + ' [label="' + row["kind"] + '"];')
            lines.append("}")
            return "\n".join(lines) + "\n"

        def graph(self, format_name="json", output=None):
            require(format_name in ("json", "mermaid", "dot"), "GRAPH_FORMAT", "Choose json, mermaid, or dot")
            with self.state() as state:
                nodes, edges = self._projection_nodes(state)
                payload = {"format": "verimission-graph-v1", "source": self.source_witness(state), "authoritative": False,
                           "nodes": nodes, "edges": edges, "filters": {"mission": "current", "history": "preserved"},
                           "limitations": ["Projection only; it does not mutate canonical state.",
                                           "Declared links do not prove semantic truth, completeness, or authorization."]}
            payload["payload_sha256"] = digest(payload)
            if output:
                if format_name == "json":
                    self.write_view(output, payload)
                else:
                    path = self.project_file(output, exists=False)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(self._graph_text(payload, format_name), encoding="utf-8")
            return payload if format_name == "json" else {"format": format_name, "source": payload["source"], "output": output,
                                                            "nodes": len(nodes), "edges": len(edges), "authoritative": False,
                                                            "payload_sha256": payload["payload_sha256"]}

        @staticmethod
        def _usage_row(row):
            required = {"provider", "model", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "cost"}
            require(isinstance(row, dict) and set(row) == required and nonempty(row["provider"]) and nonempty(row["model"]),
                    "RUN_USAGE", "Usage rows require provider, model, four token counters, and cost")
            for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                require(row[key] is None or (type(row[key]) is int and row[key] >= 0), "RUN_USAGE", key + " must be null (unknown) or a nonnegative observed integer")
            cost = row["cost"]
            require(isinstance(cost, dict) and set(cost) == {"status", "amount_usd", "method", "pricing_ref"} and
                    cost["status"] in COST_STATES and nonempty(cost["method"]), "RUN_COST", "Cost requires status, amount_usd, method, and pricing_ref")
            if cost["status"] == "unpriced":
                require(cost["amount_usd"] is None, "RUN_COST", "Unpriced cost must be null, never zero")
            else:
                require(type(cost["amount_usd"]) in (int, float) and math.isfinite(cost["amount_usd"]) and cost["amount_usd"] >= 0,
                        "RUN_COST", "Actual/estimated cost must be a finite nonnegative USD amount")
                require(nonempty(cost["pricing_ref"]), "RUN_COST", "Priced cost requires a pricing or receipt reference")

        def run_import(self, entry, agent):
            required = {"format", "id", "agent", "source", "status", "started_at", "ended_at", "attempt", "retry_of", "usage", "subagents", "notes"}
            require(agent in AGENTS and isinstance(entry, dict) and set(entry) == required and entry["format"] == "verimission-explicit-run-v1" and entry["agent"] == agent,
                    "RUN_IMPORT", "Use the explicit run template and match the selected adapter")
            require(nonempty(entry["id"]) and entry["status"] in RUN_STATES and type(entry["attempt"]) is int and entry["attempt"] >= 1,
                    "RUN_IMPORT", "Run id, recognized status, and positive attempt are required")
            started = self._iso(entry["started_at"], "started_at")
            ended = self._iso(entry["ended_at"], "ended_at", optional=True)
            require(ended is None or ended >= started, "RUN_TIME", "ended_at cannot precede started_at")
            require((entry["status"] in ("interrupted", "unknown")) or ended is not None, "RUN_TIME", "Completed and failed runs require ended_at")
            source = entry["source"]
            require(isinstance(source, dict) and set(source) == {"path", "format", "record_locator"} and
                    all(nonempty(source[key]) for key in source), "RUN_SOURCE", "Source path, declared format, and record locator are required")
            source_path = self.project_file(source["path"])
            require(isinstance(entry["usage"], list) and entry["usage"], "RUN_USAGE", "At least one usage row is required; use unpriced when cost is unavailable")
            for row in entry["usage"]:
                self._usage_row(row)
            require(isinstance(entry["subagents"], list) and len(set(entry["subagents"])) == len(entry["subagents"]) and
                    all(nonempty(value) and value != entry["id"] for value in entry["subagents"]), "RUN_SUBAGENT", "Subagent run IDs must be unique strings")
            require(entry["retry_of"] is None or nonempty(entry["retry_of"]), "RUN_RETRY", "retry_of must be null or an existing run ID")
            with self.state(write=True) as state:
                runs = state.setdefault("agent_runs", {})
                require(entry["id"] not in runs, "RUN_EXISTS", "Run IDs are immutable")
                if entry["retry_of"] is not None:
                    require(entry["retry_of"] in runs and entry["retry_of"] != entry["id"], "RUN_RETRY", "Retries must reference an imported earlier run")
                require(all(value in runs for value in entry["subagents"]), "RUN_SUBAGENT", "Import referenced subagent runs before the parent")
                value = {**entry, "source": {**source, "sha256": file_digest(source_path)}, "imported_at": now(),
                         "adapter": {"agent": agent, "mode": "explicit_hashed_import", "native_format_parsed": False},
                         "claims_promoted": False, "mission_changed": False, "authorization_granted": False,
                         "unknown_outcome_replayed": False}
                runs[entry["id"]] = value
                self.event(state, "agent-run-imported", entry["id"], {"agent": agent, "status": entry["status"]})
                return value

        @staticmethod
        def adapter_template(agent):
            require(agent in AGENTS, "ADAPTER", "Choose codex, opencode, claude, or hermes")
            return {"format": "verimission-explicit-run-v1", "id": "RUN-UNIQUE", "agent": agent,
                    "source": {"path": "evidence/agent-run.jsonl", "format": "declare-real-export-format", "record_locator": "turn/session/event identifier"},
                    "status": "unknown", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None,
                    "attempt": 1, "retry_of": None,
                    "usage": [{"provider": "unknown", "model": "unknown", "input_tokens": None, "output_tokens": None,
                               "cache_read_tokens": None, "cache_write_tokens": None,
                               "cost": {"status": "unpriced", "amount_usd": None, "method": "provider price unavailable", "pricing_ref": ""}}],
                    "subagents": [], "notes": "Transcribe only fields supported by the hashed source; unknown is not zero except literal observed token counters."}

        def cost_summary(self):
            with self.state() as state:
                runs = list(state.get("agent_runs", {}).values())
                witness = self.source_witness(state)
            totals = {"actual_usd": 0.0, "estimated_usd": 0.0, "unpriced_rows": 0,
                      "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0,
                      "unreported_token_fields": 0}
            by_agent = {agent: {"runs": 0, "actual_usd": 0.0, "estimated_usd": 0.0, "unpriced_rows": 0} for agent in AGENTS}
            for run in runs:
                by_agent[run["agent"]]["runs"] += 1
                for row in run["usage"]:
                    for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                        if row[key] is None:
                            totals["unreported_token_fields"] += 1
                        else:
                            totals[key] += row[key]
                    cost = row["cost"]
                    if cost["status"] == "unpriced":
                        totals["unpriced_rows"] += 1
                        by_agent[run["agent"]]["unpriced_rows"] += 1
                    else:
                        field = cost["status"] + "_usd"
                        totals[field] += cost["amount_usd"]
                        by_agent[run["agent"]][field] += cost["amount_usd"]
            subagent_links = sum(len(run["subagents"]) for run in runs)
            return {"format": "verimission-cost-summary-v1", "source": witness, "runs": len(runs),
                    "attempt_records": len(runs), "retry_runs": sum(run["retry_of"] is not None for run in runs),
                    "subagent_links": subagent_links, "possible_parent_child_double_counting": subagent_links > 0,
                    "totals": totals, "by_agent": by_agent,
                    "complete_cost_total_available": totals["unpriced_rows"] == 0,
                    "limitations": ["Actual and estimated amounts are reported separately.",
                                    "Unpriced usage is unknown, not zero.",
                                    "Imported metadata is not authenticated by the harness beyond hashing the referenced source file."]}

        @staticmethod
        def _git(root, argv):
            result = subprocess.run(["git", *argv], cwd=root, shell=False, capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, "GIT_REPORT", "Git could not resolve the requested report inputs")
            return result.stdout.strip()

        def pr_report(self, base_ref, head_ref, output=None, format_name="markdown"):
            require(format_name in ("json", "markdown") and all(nonempty(value) and len(value) <= 256 and not value.startswith("-") for value in (base_ref, head_ref)),
                    "PR_REPORT", "Choose json/markdown and explicit safe Git refs")
            base = self._git(self.root, ["rev-parse", "--verify", base_ref + "^{commit}"])
            head = self._git(self.root, ["rev-parse", "--verify", head_ref + "^{commit}"])
            changed = []
            raw = self._git(self.root, ["diff", "--name-status", "--find-renames", base, head, "--"])
            for line in raw.splitlines() if raw else []:
                parts = line.split("\t")
                changed.append({"status": parts[0], "paths": parts[1:]})
            audit = self.validate()
            with self.state() as state:
                witness = self.source_witness(state)
                matrix = self.matrix(state)
                cycles = [row for row in state["cycles"] if row["mission_hash"] == state["mission_hash"]]
                checks = [{"cycle": cycle["id"], "criterion": check["criterion"], "passed": check["passed"],
                           "outcome": check["outcome"], "output_sha256": check["output_sha256"], "artifacts": check["artifacts"]}
                          for cycle in cycles for check in cycle["checks"]]
                claims = [{"id": row["id"], "status": row["status"], "kind": row["kind"], "statement": row["statement"]}
                          for row in state["claims"].values()]
                tasks = [row for row in state.get("tasks", {}).values() if row["mission_hash"] == state["mission_hash"]]
                require(self.source_witness(state) == witness, "ASSESSMENT_DRIFT", "State changed while building the report")
            req_verified = sum(row["status"] == "verified_in_declared_scope" for row in matrix["requirements"])
            criterion_verified = sum(row["status"] == "verified_in_declared_scope" for row in matrix["criteria"])
            payload = {"format": "verimission-pr-report-v1", "git": {"base_ref": base_ref, "base_commit": base, "head_ref": head_ref, "head_commit": head,
                                                                            "changed_files": changed, "changed_file_count": len(changed)},
                       "source": witness, "audit": audit, "scope": {"objective": state["mission"]["objective"],
                                                                          "in_scope": state["mission"]["in_scope"], "out_of_scope": state["mission"]["out_of_scope"]},
                       "coverage": {"requirements": {"verified": req_verified, "total": len(matrix["requirements"])},
                                    "criteria": {"verified": criterion_verified, "total": len(matrix["criteria"])},
                                    "tasks": {"done": sum(row["status"] == "done" for row in tasks), "total": len(tasks)},
                                    "changed_files": {"verified": None, "total": len(changed), "status": "indeterminate_without_explicit_file_to_criterion_mapping"}},
                       "checks": checks, "claims": claims, "retractions": [row for row in claims if row["status"] == "retracted"],
                       "traceability": matrix, "human_review": {"required": True,
                           "questions": ["Do the tests discriminate the relevant failures?", "Does the diff stay within authorized scope?",
                                         "Are coverage denominators and exclusions complete?", "Do claims stay below the evidence ceiling?"]},
                       "limitations": ["A passing check does not prove test quality or production correctness.",
                                       "Git diff membership does not prove a changed file was semantically verified.",
                                       "This report is a read-only projection and does not approve or merge a PR."]}
            payload["payload_sha256"] = digest(payload)
            if output:
                if format_name == "json":
                    self.write_view(output, payload)
                else:
                    path = self.project_file(output, exists=False)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    lines = ["# VeriMission PR report", "", "- Base: `" + base + "`", "- Head: `" + head + "`",
                             "- State revision: `" + str(witness["state_revision"]) + "`", "- Human review: **required**", "",
                             "## Coverage", "", "| Universe | Verified | Total |", "| --- | ---: | ---: |",
                             "| Requirements | " + str(req_verified) + " | " + str(len(matrix["requirements"])) + " |",
                             "| Criteria | " + str(criterion_verified) + " | " + str(len(matrix["criteria"])) + " |",
                             "| Tasks done | " + str(sum(row["status"] == "done" for row in tasks)) + " | " + str(len(tasks)) + " |",
                             "| Changed files | indeterminate | " + str(len(changed)) + " |", "", "## Changed files", ""]
                    lines.extend("- `" + item["status"] + "` " + ", ".join("`" + path + "`" for path in item["paths"]) for item in changed)
                    lines.extend(["", "## Checks", ""])
                    lines.extend("- Cycle " + str(row["cycle"]) + " / `" + row["criterion"] + "`: " + ("passed" if row["passed"] else "not passed") for row in checks)
                    lines.extend(["", "## Claims and retractions", ""])
                    lines.extend("- `" + row["id"] + "` — " + row["status"] + ": " + row["statement"] for row in claims)
                    lines.extend(["", "## Required human review", ""] + ["- " + question for question in payload["human_review"]["questions"]] +
                                 ["", "## Limitations", ""] + ["- " + value for value in payload["limitations"]] +
                                 ["", "Payload SHA-256: `" + payload["payload_sha256"] + "`", ""])
                    path.write_text("\n".join(lines), encoding="utf-8")
            return payload

        def validate(self):
            result = super().validate()
            with self.state() as state:
                runs = state.get("agent_runs", {})
                for run in runs.values():
                    if run["retry_of"] is not None and run["retry_of"] not in runs:
                        result["issues"].append({"kind": "broken_run_retry", "run": run["id"]})
                    if any(value not in runs for value in run["subagents"]):
                        result["issues"].append({"kind": "broken_subagent_link", "run": run["id"]})
                    if run.get("claims_promoted") or run.get("mission_changed") or run.get("authorization_granted"):
                        result["issues"].append({"kind": "unsafe_run_import", "run": run["id"]})
            result["passed"] = not result["issues"]
            return result

        def capabilities(self):
            result = super().capabilities()
            result["v81"] = {"read_only_graph": ["json", "mermaid", "dot"], "pr_report": ["json", "markdown"],
                             "cost_accounting": ["actual", "estimated", "unpriced"],
                             "explicit_import_adapters": list(AGENTS), "native_log_parsers": False,
                             "agent_dispatch": False, "claim_promotion_from_import": False}
            return result

    return Harness81
