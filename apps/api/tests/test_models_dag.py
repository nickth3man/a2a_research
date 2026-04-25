"""Tests for ClaimDAG: topological sort, traversal, cycle handling."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core import ClaimDAG, ClaimDependency


class TestClaimDependency:
    def test_default_relation(self):
        d = ClaimDependency(parent_id="a", child_id="b")
        assert d.relation == "presupposes"

    def test_all_relation_types(self):
        for rel in ("presupposes", "refines", "contrasts"):
            d = ClaimDependency(parent_id="a", child_id="b", relation=rel)
            assert d.relation == rel

    def test_invalid_relation(self):
        with pytest.raises(ValidationError):
            ClaimDependency(parent_id="a", child_id="b", relation="invalid")


class TestClaimDAG:
    def test_empty_dag(self):
        dag = ClaimDAG()
        assert dag.nodes == []
        assert dag.edges == []
        assert dag.topological_order() == []
        assert dag.parents_of("x") == []
        assert dag.children_of("x") == []
        assert dag.descendants_of("x") == []

    def test_single_node(self):
        dag = ClaimDAG(nodes=["a"])
        assert dag.topological_order() == ["a"]

    def test_linear_chain(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="b", child_id="c"),
            ],
        )
        order = dag.topological_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_shape(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c", "d"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="a", child_id="c"),
                ClaimDependency(parent_id="b", child_id="d"),
                ClaimDependency(parent_id="c", child_id="d"),
            ],
        )
        order = dag.topological_order()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_parents_of(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="c"),
                ClaimDependency(parent_id="b", child_id="c"),
            ],
        )
        assert set(dag.parents_of("c")) == {"a", "b"}
        assert dag.parents_of("a") == []
        assert dag.parents_of("nonexistent") == []

    def test_children_of(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="a", child_id="c"),
            ],
        )
        assert set(dag.children_of("a")) == {"b", "c"}
        assert dag.children_of("b") == []

    def test_descendants_of_direct(self):
        dag = ClaimDAG(
            nodes=["a", "b"],
            edges=[ClaimDependency(parent_id="a", child_id="b")],
        )
        assert dag.descendants_of("a") == ["b"]

    def test_descendants_of_transitive(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="b", child_id="c"),
            ],
        )
        assert dag.descendants_of("a") == ["b", "c"]

    def test_descendants_of_leaf(self):
        dag = ClaimDAG(
            nodes=["a", "b"],
            edges=[ClaimDependency(parent_id="a", child_id="b")],
        )
        assert dag.descendants_of("b") == []

    def test_descendants_of_self_loop_prevented(self):
        dag = ClaimDAG(
            nodes=["a"],
            edges=[ClaimDependency(parent_id="a", child_id="a")],
        )
        assert dag.descendants_of("a") == []

    def test_cycle_partial_topo(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="b", child_id="c"),
                ClaimDependency(parent_id="c", child_id="b"),
            ],
        )
        order = dag.topological_order()
        assert "a" in order
        assert "b" not in order
        assert "c" not in order

    def test_disconnected_components(self):
        dag = ClaimDAG(
            nodes=["a", "b", "c", "d"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="c", child_id="d"),
            ],
        )
        order = dag.topological_order()
        assert set(order) == {"a", "b", "c", "d"}
        assert order.index("a") < order.index("b")
        assert order.index("c") < order.index("d")

    def test_node_not_in_nodes_but_in_edge(self):
        dag = ClaimDAG(
            nodes=["a"],
            edges=[ClaimDependency(parent_id="a", child_id="z")],
        )
        order = dag.topological_order()
        assert "a" in order
        assert "z" in order
