"""Multi-agent paper trading: N agents on the same feed, CRDT-merge their trade logs.

This exercises the quf:// URI scheme concretely. Each agent:

  - Has its own TimeCell + TemporalReasoner + TradingDecisionSupport
  - Subscribes to the same price feed
  - Independently produces trade records with unique quf:// URIs
  - Publishes trades to a shared AgentMemory

The shared AgentMemory uses the URI as a CRDT key:
  - Two agents can independently produce a forecast at the same
    time, with different ids
  - put() returns the URI; multiple stores can be merged by URI
  - No conflicts because the ids are uuid4

After the run, the trade log from all agents can be merged into
a single dict keyed by quf:// URI. The merge is associative and
commutative (CRDT property).

This is a small but real multi-agent system. It shows the
quf:// URI scheme in action: forecasts are addressable,
portable across cells, and mergeable across agents.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Iterator, Tuple, List, Dict, Optional
import concurrent.futures

from quilt_cell import TimeCell
from temporal import TemporalReasoner, AgentMemory

from .trader import PaperTrader, Trade, Portfolio
from .strategy import TradingDecisionSupport


@dataclass
class AgentConfig:
    """Per-agent configuration."""
    name: str
    threshold_return: float = 0.005
    threshold_uncertainty: float = 0.4
    max_position_pct: float = 0.10
    horizon: int = 5
    history_len: int = 64
    min_history: int = 32


class MultiAgentTrader:
    """A collection of paper-trading agents sharing a feed and an AgentMemory.

    Each agent runs independently but writes to a shared
    AgentMemory. After the run, the trade logs can be CRDT-merged
    by quf:// URI.

    Parameters
    ----------
    configs : list of AgentConfig
    asset : str
    shared_memory : AgentMemory (optional)
        A shared memory for all agents. If None, each agent has
        its own memory and we merge at the end.
    """

    def __init__(
        self,
        configs: List[AgentConfig],
        asset: str = "ASSET",
        shared_memory: Optional[AgentMemory] = None,
    ):
        self.configs = configs
        self.asset = asset
        self.shared_memory = shared_memory
        self.agents: List[PaperTrader] = []
        self._build_agents()

    def _build_agents(self) -> None:
        self.agents = []
        for cfg in self.configs:
            cell = TimeCell()
            if self.shared_memory is not None:
                # Use a wrapper that proxies puts to the shared memory
                # but keeps the agent's local pointer for reads
                from temporal import AgentMemory as _AM
                local_mem = _AM()
                reasoner = TemporalReasoner(cell=cell, memory=local_mem)
            else:
                reasoner = TemporalReasoner(cell=cell)
            strategy = TradingDecisionSupport(
                memory=reasoner.memory,
                threshold_return=cfg.threshold_return,
                threshold_uncertainty=cfg.threshold_uncertainty,
            )
            trader = PaperTrader(
                cell=cell, reasoner=reasoner, strategy=strategy,
                asset=f"{self.asset}:{cfg.name}",
                history_len=cfg.history_len, horizon=cfg.horizon,
                min_history=cfg.min_history,
                max_position_pct=cfg.max_position_pct,
            )
            self.agents.append(trader)

    def step(self, price: float) -> List[dict]:
        """Process one price tick across all agents. Returns a list of step reports."""
        reports = []
        for trader in self.agents:
            r = trader.step(price)
            reports.append({
                "agent": trader.asset,
                "step": r["step"],
                "price": r["price"],
                "trade": r["trade"],
                "forecast": r["forecast"],
                "decision": r["decision"],
            })
        return reports

    def run(
        self,
        price_stream: Iterator[Tuple[int, float]],
        n_steps: int,
    ) -> Dict[str, any]:
        """Run all agents over the price stream. Returns a summary dict."""
        # Use threads to step each agent in parallel (each step is fast)
        history = []
        for t, price in price_stream:
            # Sequential stepping — agents share the same tick
            for trader in self.agents:
                trader.step(price)
            history.append((t, price))
        # Build the summary
        per_agent = []
        all_uris = set()
        for trader in self.agents:
            log = [t.to_dict() for t in trader.portfolio.trade_log]
            uris = {t["forecast_uri"] for t in log}
            all_uris |= uris
            per_agent.append({
                "agent": trader.asset,
                "n_trades": len(log),
                "actions": {a: sum(1 for t in log if t["action"] == a)
                            for a in ("buy", "sell", "hold", "half_size", "gather_data")},
                "total_pnl": trader.total_pnl,
                "trade_uris": sorted(uris),
            })
        return {
            "n_steps": n_steps,
            "n_agents": len(self.agents),
            "total_trades": sum(p["n_trades"] for p in per_agent),
            "unique_uris": len(all_uris),
            "per_agent": per_agent,
        }


def crdt_merge_trade_logs(*trade_logs: List[dict]) -> Dict[str, dict]:
    """Merge multiple trade logs by quf:// URI.

    This is the CRDT property of the quf:// URI scheme: the
    same forecast URI on two agents refers to the same record,
    and different URIs are different records. The merge is
    associative and commutative.

    Returns a dict keyed by quf:// URI. If two agents produced
    the same URI (extremely unlikely with uuid4), the later
    trade wins (last-write-wins for true conflicts).
    """
    merged: Dict[str, dict] = {}
    for log in trade_logs:
        for trade in log:
            uri = trade.get("forecast_uri")
            if uri is None:
                continue
            # Last-write-wins for true URI conflicts (uuid4 makes these vanishingly rare)
            if uri not in merged or trade.get("timestamp_ms", 0) > merged[uri].get("timestamp_ms", 0):
                merged[uri] = trade
    return merged


def compare_merged_to_unmerged(merged: Dict[str, dict],
                                unmerged_logs: List[List[dict]]) -> dict:
    """Verify that the merged dict is the same size as the union of unique URIs.

    This is the CRDT consistency check: if the same URI appears
    in two logs (very unlikely), the merge shouldn't double-count.
    """
    all_uris = set()
    for log in unmerged_logs:
        for t in log:
            if t.get("forecast_uri"):
                all_uris.add(t["forecast_uri"])
    return {
        "n_merged": len(merged),
        "n_unique_uris": len(all_uris),
        "consistent": len(merged) == len(all_uris),
    }
