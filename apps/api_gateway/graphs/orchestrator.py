from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from apps.api_gateway.graphs.state import AppointmentState, LeadIntakeState, ReplyState


def run_lead_intake(service, dealership_id: str, payload):
    graph = StateGraph(LeadIntakeState)
    graph.add_node("qualification_agent", lambda state: service._prepare_lead_state(state["dealership_id"], state["payload"]))
    graph.add_node("routing_agent", lambda state: service._assign_rep_from_state(state))
    graph.add_node("merge_agent", lambda state: {"lead": service._merge_duplicate_from_state(state)})
    graph.add_node("persistence_agent", lambda state: {"lead": service._persist_new_from_state(state)})

    graph.add_edge(START, "qualification_agent")
    graph.add_conditional_edges(
        "qualification_agent",
        lambda state: "merge_agent" if state.get("duplicate_found") else "routing_agent",
        {"merge_agent": "merge_agent", "routing_agent": "routing_agent"},
    )
    graph.add_edge("routing_agent", "persistence_agent")
    graph.add_edge("merge_agent", END)
    graph.add_edge("persistence_agent", END)
    compiled = graph.compile()
    result = compiled.invoke({"dealership_id": dealership_id, "payload": payload})
    return result["lead"]


def run_reply_graph(service, dealership_id: str, payload):
    graph = StateGraph(ReplyState)
    graph.add_node("context_agent", lambda state: {"context": service._load_reply_context(state["dealership_id"], state["payload"])})
    graph.add_node("classification_agent", lambda state: {"classification": service._classify_reply_context(state)})
    graph.add_node("retrieval_agent", lambda state: {"retrieval": service._retrieve_reply_materials(state)})
    graph.add_node("nurture_agent", lambda state: {"reply": service._compose_reply_from_state(state)})
    graph.add_node("persistence_agent", lambda state: {"response": service._persist_reply_from_state(state)})

    graph.add_edge(START, "context_agent")
    graph.add_edge("context_agent", "classification_agent")
    graph.add_edge("classification_agent", "retrieval_agent")
    graph.add_edge("retrieval_agent", "nurture_agent")
    graph.add_edge("nurture_agent", "persistence_agent")
    graph.add_edge("persistence_agent", END)
    compiled = graph.compile()
    result = compiled.invoke({"dealership_id": dealership_id, "payload": payload})
    return result["response"]


def run_booking_graph(service, dealership_id: str, payload, background_tasks=None):
    graph = StateGraph(AppointmentState)
    graph.add_node("inventory_validation_agent", lambda state: {"validation": service._validate_booking_request(state["dealership_id"], state["payload"])})
    graph.add_node("scheduling_agent", lambda state: {"appointment": service._persist_booking(state, state.get("background_tasks"))})
    graph.add_edge(START, "inventory_validation_agent")
    graph.add_edge("inventory_validation_agent", "scheduling_agent")
    graph.add_edge("scheduling_agent", END)
    compiled = graph.compile()
    result = compiled.invoke({"dealership_id": dealership_id, "payload": payload, "background_tasks": background_tasks})
    return result["appointment"]


def run_reschedule_graph(service, dealership_id: str, payload, background_tasks=None):
    graph = StateGraph(AppointmentState)
    graph.add_node("inventory_validation_agent", lambda state: {"validation": service._validate_reschedule_request(state["dealership_id"], state["payload"])})
    graph.add_node("scheduling_agent", lambda state: {"appointment": service._persist_reschedule(state, state.get("background_tasks"))})
    graph.add_edge(START, "inventory_validation_agent")
    graph.add_edge("inventory_validation_agent", "scheduling_agent")
    graph.add_edge("scheduling_agent", END)
    compiled = graph.compile()
    result = compiled.invoke({"dealership_id": dealership_id, "payload": payload, "background_tasks": background_tasks})
    return result["appointment"]
