"""Tests for Navigator integration, EXTEND_GRAPH, and multi-step sidequests.

This module tests the enhanced navigation capabilities:
1. EXTEND_GRAPH handling (map gap proposals)
2. Multi-step sidequest execution
3. ReturnBehavior enforcement
4. graph_patch_suggested event emission
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from swarm.runtime.navigator import (
    Navigator,
    NavigatorInput,
    NavigatorOutput,
    NextStepBrief,
    RouteIntent,
    RouteProposal,
    ProposedEdge,
    ProposedNode,
    EdgeCandidate,
    VerificationSummary,
    StallSignals,
    navigator_output_to_dict,
    navigator_output_from_dict,
)
from swarm.runtime.navigator_integration import (
    NavigationOrchestrator,
    NavigationResult,
    apply_extend_graph_request,
    check_and_handle_detour_completion,
    emit_graph_patch_suggested_event,
)
from swarm.runtime.sidequest_catalog import (
    SidequestCatalog,
    SidequestDefinition,
    SidequestStep,
    ReturnBehavior,
)
from swarm.runtime.types import RunState, RoutingDecision


class TestProposedNodeType:
    """Tests for ProposedNode type."""

    def test_proposed_node_with_template_id(self):
        """ProposedNode can be created with template_id."""
        node = ProposedNode(
            template_id="security-scanner",
            objective="Audit the auth changes",
        )
        assert node.get_target_id() == "security-scanner"
        assert node.objective == "Audit the auth changes"

    def test_proposed_node_with_station_id(self):
        """ProposedNode can be created with station_id."""
        node = ProposedNode(
            station_id="clarifier",
            objective="Clarify requirements",
        )
        assert node.get_target_id() == "clarifier"

    def test_proposed_node_station_takes_priority(self):
        """station_id takes priority over template_id."""
        node = ProposedNode(
            template_id="template-1",
            station_id="station-1",
        )
        assert node.get_target_id() == "station-1"


class TestProposedEdgeSerialization:
    """Tests for ProposedEdge with ProposedNode serialization."""

    def test_proposed_edge_with_node_to_dict(self):
        """ProposedEdge with ProposedNode serializes correctly."""
        edge = ProposedEdge(
            from_node="step-1",
            to_node="security-scanner",
            why="Security-sensitive files changed",
            proposed_node=ProposedNode(
                template_id="security-scanner",
                objective="Audit auth changes",
                params={"severity": "high"},
            ),
        )

        output = NavigatorOutput(
            route=RouteProposal(intent=RouteIntent.EXTEND_GRAPH),
            next_step_brief=NextStepBrief(objective="Run security audit"),
            proposed_edge=edge,
        )

        data = navigator_output_to_dict(output)
        assert "proposed_edge" in data
        assert data["proposed_edge"]["from_node"] == "step-1"
        assert data["proposed_edge"]["to_node"] == "security-scanner"
        assert "proposed_node" in data["proposed_edge"]
        assert data["proposed_edge"]["proposed_node"]["template_id"] == "security-scanner"

    def test_proposed_edge_from_dict_with_node(self):
        """ProposedEdge with ProposedNode deserializes correctly."""
        data = {
            "route": {"intent": "extend_graph"},
            "next_step_brief": {"objective": "Run audit"},
            "proposed_edge": {
                "from_node": "step-1",
                "to_node": "security-scanner",
                "why": "Security files changed",
                "proposed_node": {
                    "template_id": "security-scanner",
                    "objective": "Audit",
                    "params": {"level": "strict"},
                },
            },
        }

        output = navigator_output_from_dict(data)
        assert output.proposed_edge is not None
        assert output.proposed_edge.proposed_node is not None
        assert output.proposed_edge.proposed_node.template_id == "security-scanner"
        assert output.proposed_edge.proposed_node.params == {"level": "strict"}


class TestExtendGraphHandling:
    """Tests for EXTEND_GRAPH request handling."""

    def test_apply_extend_graph_creates_injected_node(self):
        """apply_extend_graph_request creates an injected node."""
        nav_output = NavigatorOutput(
            route=RouteProposal(
                intent=RouteIntent.EXTEND_GRAPH,
                target_node="clarifier",
            ),
            next_step_brief=NextStepBrief(objective="Clarify"),
            proposed_edge=ProposedEdge(
                from_node="step-1",
                to_node="clarifier",
                why="Ambiguity detected",
                is_return=True,
            ),
        )

        run_state = RunState(run_id="test-run", flow_key="build")

        target = apply_extend_graph_request(
            nav_output=nav_output,
            run_state=run_state,
            current_node="step-1",
        )

        assert target == "clarifier"
        assert len(run_state.injected_nodes) == 1
        assert run_state.is_interrupted()

    def test_apply_extend_graph_validates_library(self):
        """apply_extend_graph_request validates target against library."""
        nav_output = NavigatorOutput(
            route=RouteProposal(intent=RouteIntent.EXTEND_GRAPH),
            next_step_brief=NextStepBrief(objective=""),
            proposed_edge=ProposedEdge(
                from_node="step-1",
                to_node="nonexistent-station",
                why="Try this",
            ),
        )

        run_state = RunState(run_id="test-run", flow_key="build")

        target = apply_extend_graph_request(
            nav_output=nav_output,
            run_state=run_state,
            current_node="step-1",
            station_library=["clarifier", "fixer"],  # nonexistent not in list
        )

        assert target is None
        assert len(run_state.injected_nodes) == 0

    def test_apply_extend_graph_no_return(self):
        """apply_extend_graph_request with is_return=False doesn't push stack."""
        nav_output = NavigatorOutput(
            route=RouteProposal(intent=RouteIntent.EXTEND_GRAPH),
            next_step_brief=NextStepBrief(objective=""),
            proposed_edge=ProposedEdge(
                from_node="step-1",
                to_node="clarifier",
                why="One-shot",
                is_return=False,  # No return
            ),
        )

        run_state = RunState(run_id="test-run", flow_key="build")

        target = apply_extend_graph_request(
            nav_output=nav_output,
            run_state=run_state,
            current_node="step-1",
        )

        assert target == "clarifier"
        assert len(run_state.injected_nodes) == 1
        assert not run_state.is_interrupted()  # No interruption frame


class TestMultiStepSidequests:
    """Tests for multi-step sidequest execution."""

    def test_sidequest_is_multi_step(self):
        """Multi-step sidequests are correctly identified."""
        single_step = SidequestDefinition(
            sidequest_id="simple",
            name="Simple",
            description="Single step",
            station_id="clarifier",
        )
        assert not single_step.is_multi_step

        multi_step = SidequestDefinition(
            sidequest_id="complex",
            name="Complex",
            description="Multiple steps",
            steps=[
                SidequestStep(template_id="context-loader"),
                SidequestStep(template_id="fixer"),
                SidequestStep(template_id="test-runner"),
            ],
        )
        assert multi_step.is_multi_step

    def test_sidequest_to_steps_legacy(self):
        """to_steps() converts legacy single-station format."""
        sidequest = SidequestDefinition(
            sidequest_id="legacy",
            name="Legacy",
            description="Old format",
            station_id="clarifier",
            objective_template="Clarify: {{issue}}",
        )

        steps = sidequest.to_steps()
        assert len(steps) == 1
        assert steps[0].template_id == "clarifier"
        assert steps[0].objective_override == "Clarify: {{issue}}"


class TestReturnBehavior:
    """Tests for ReturnBehavior enforcement."""

    def test_return_behavior_resume(self):
        """resume mode returns to original node."""
        run_state = RunState(run_id="test-run", flow_key="build")
        run_state.push_resume("original-step", {})
        run_state.push_interruption(
            reason="Test detour",
            return_node="original-step",
            context_snapshot={"sidequest_id": "clarifier"},
        )

        catalog = SidequestCatalog([
            SidequestDefinition(
                sidequest_id="clarifier",
                name="Clarifier",
                description="Test",
                station_id="clarifier",
                return_behavior=ReturnBehavior(mode="resume"),
            )
        ])

        resume_node = check_and_handle_detour_completion(run_state, catalog)
        assert resume_node == "original-step"

    def test_return_behavior_bounce_to(self):
        """bounce_to mode goes to specific node."""
        run_state = RunState(run_id="test-run", flow_key="build")
        run_state.push_resume("original-step", {})
        run_state.push_interruption(
            reason="Test detour",
            return_node="original-step",
            context_snapshot={"sidequest_id": "redirect-sidequest"},
        )

        catalog = SidequestCatalog([
            SidequestDefinition(
                sidequest_id="redirect-sidequest",
                name="Redirect",
                description="Test",
                station_id="fixer",
                return_behavior=ReturnBehavior(
                    mode="bounce_to",
                    target_node="gate-step",
                ),
            )
        ])

        resume_node = check_and_handle_detour_completion(run_state, catalog)
        assert resume_node == "gate-step"

    def test_return_behavior_halt(self):
        """halt mode returns None (terminate flow)."""
        run_state = RunState(run_id="test-run", flow_key="build")
        run_state.push_resume("original-step", {})
        run_state.push_interruption(
            reason="Test detour",
            return_node="original-step",
            context_snapshot={"sidequest_id": "halt-sidequest"},
        )

        catalog = SidequestCatalog([
            SidequestDefinition(
                sidequest_id="halt-sidequest",
                name="Halt",
                description="Test",
                station_id="blocker",
                return_behavior=ReturnBehavior(mode="halt"),
            )
        ])

        resume_node = check_and_handle_detour_completion(run_state, catalog)
        assert resume_node is None


class TestGraphPatchEvent:
    """Tests for graph_patch_suggested event emission."""

    def test_emit_graph_patch_event(self):
        """graph_patch_suggested event contains correct patch structure."""
        events = []

        def mock_append(run_id, event):
            events.append(event)

        proposed_edge = ProposedEdge(
            from_node="step-1",
            to_node="security-scanner",
            why="Security files changed",
            edge_type="injection",
            proposed_node=ProposedNode(
                template_id="security-scanner",
                node_id="suggested-security-scanner",
            ),
        )

        emit_graph_patch_suggested_event(
            run_id="test-run",
            flow_key="build",
            step_id="step-1",
            proposed_edge=proposed_edge,
            append_event_fn=mock_append,
        )

        assert len(events) == 1
        event = events[0]
        assert event.kind == "graph_patch_suggested"
        assert event.payload["reason"] == "Security files changed"
        assert isinstance(event.payload["patch"], list)
        # Should have node patch and edge patch
        assert len(event.payload["patch"]) == 2


class TestNavigationOrchestratorExtendGraph:
    """Tests for NavigationOrchestrator EXTEND_GRAPH handling."""

    def test_orchestrator_handles_extend_graph(self):
        """NavigationOrchestrator correctly handles EXTEND_GRAPH intent."""
        # Create a mock Navigator that returns EXTEND_GRAPH
        mock_navigator = MagicMock()
        mock_navigator.navigate.return_value = NavigatorOutput(
            route=RouteProposal(
                intent=RouteIntent.EXTEND_GRAPH,
                target_node="clarifier",
            ),
            next_step_brief=NextStepBrief(objective="Clarify requirements"),
            proposed_edge=ProposedEdge(
                from_node="current",
                to_node="clarifier",
                why="Ambiguity detected",
                is_return=True,
            ),
        )

        # Create mock flow graph
        mock_flow_graph = MagicMock()
        mock_flow_graph.get_outgoing_edges.return_value = []

        orchestrator = NavigationOrchestrator(navigator=mock_navigator)
        run_state = RunState(run_id="test-run", flow_key="build")

        with patch("swarm.runtime.navigator_integration.emit_graph_patch_suggested_event"):
            result = orchestrator.navigate(
                run_id="test-run",
                flow_key="build",
                current_node="current",
                iteration=1,
                flow_graph=mock_flow_graph,
                step_result={"status": "UNVERIFIED"},
                verification_result=None,
                file_changes=None,
                run_state=run_state,
            )

        assert result.extend_graph_injected
        assert result.next_node == "clarifier"
