from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.contact_priority import evaluate_contact_priority
from src.demo_data import build_demo_customers
from src.tracking import ContactStatus, CustomerTracking, ResponseStatus

st.set_page_config(page_title="CS Operations Hub Lite", page_icon="🧭", layout="wide")

PRIORITY_LABELS = {"High": "Alta", "Medium": "Média", "Low": "Baixa"}
HEALTH_LABELS = {
    "Healthy": "Ativo",
    "AtRisk": "Em risco",
    "Dormant": "Dormente",
    "NeverActivated": "Nunca ativou",
}
ACTION_LABELS = {
    "Contact today": "Fazer contato hoje",
    "Follow up today": "Fazer follow-up hoje",
    "Follow up tomorrow": "Fazer follow-up amanhã",
    "Wait for response": "Aguardar resposta",
    "Reactivate customer": "Tentar reativação",
    "Schedule renewal conversation": "Agendar conversa de renovação",
    "No action": "Sem ação imediata",
}
CUSTOMER_STATUS_LABELS = {
    "Active": "Ativo",
    "Cancelled": "Cancelado",
    "Desistencia": "Desistência",
}
CUSTOMER_STATUS_VALUES = {label: value for value, label in CUSTOMER_STATUS_LABELS.items()}

st.markdown(
    """
    <style>
    .block-container{padding-top:1.5rem;padding-bottom:3rem}
    [data-testid="stSidebar"]{background:#f7f7f8;border-right:1px solid #e5e7eb}
    [data-testid="stMetric"]{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:12px 14px}
    .eyebrow{font-size:.76rem;text-transform:uppercase;letter-spacing:.1em;color:#c62828;font-weight:800}
    .demo-banner{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:10px 14px;margin-bottom:18px}
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_date(value):
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed.date()


def build_tracking(row: pd.Series) -> CustomerTracking:
    renewal = row.get("renewal_days")
    return CustomerTracking(
        customer_id=str(row.get("customer_id") or ""),
        customer_name=str(row.get("customer_name") or ""),
        owner=str(row.get("owner") or "") or None,
        last_contact_date=normalize_date(row.get("last_contact_date")),
        next_contact_date=normalize_date(row.get("next_contact_date")),
        contact_status=ContactStatus(str(row.get("contact_status") or "Not contacted")),
        response_status=ResponseStatus(str(row.get("response_status") or "Not applicable")),
        follow_up_count=int(row.get("follow_up_count") or 0),
        renewal_days=None if renewal is None or pd.isna(renewal) else int(renewal),
        notes=str(row.get("notes") or "") or None,
    )


def active_portfolio(customers: pd.DataFrame) -> pd.DataFrame:
    active = customers[customers["customer_status"] == "Active"].copy().reset_index(drop=True)
    results = [evaluate_contact_priority(build_tracking(row), today=date.today()) for _, row in active.iterrows()]
    active = pd.concat([active, pd.DataFrame(results)], axis=1)
    active["priority_display"] = active["contact_priority"].map(PRIORITY_LABELS)
    active["health_display"] = active["platform_status"].map(HEALTH_LABELS)
    active["action_display"] = active["next_contact_action"].map(ACTION_LABELS).fillna(active["next_contact_action"])
    return active


def overview(customers: pd.DataFrame) -> None:
    active = active_portfolio(customers)
    st.markdown('<div class="eyebrow">Operação diária</div>', unsafe_allow_html=True)
    st.title("O que precisa da sua atenção hoje")
    health = active["platform_status"].value_counts()
    metrics = st.columns(6)
    metrics[0].metric("Total ativos", len(active))
    metrics[1].metric("Ativo", int(health.get("Healthy", 0)))
    metrics[2].metric("Em risco", int(health.get("AtRisk", 0)))
    metrics[3].metric("Dormente", int(health.get("Dormant", 0)))
    metrics[4].metric("Nunca ativou", int(health.get("NeverActivated", 0)))
    due = active["next_contact_date"].apply(normalize_date)
    metrics[5].metric("Falar hoje", int(due.apply(lambda value: value is not None and value <= date.today()).sum()))

    health_weight = {"NeverActivated": 4, "Dormant": 3, "AtRisk": 2, "Healthy": 0}
    active["daily_score"] = active["contact_priority_score"] + active["platform_status"].map(health_weight).fillna(0) * 25
    queue = active.sort_values("daily_score", ascending=False)
    st.markdown("### Prioridades do dia")
    st.dataframe(
        queue[["customer_name", "owner", "health_display", "next_contact_date", "priority_display", "action_display", "payment_platform", "account_count"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "customer_name": "Cliente",
            "owner": "Responsável",
            "health_display": "Saúde",
            "next_contact_date": st.column_config.DateColumn("Próximo contato", format="DD/MM/YYYY"),
            "priority_display": "Prioridade",
            "action_display": "Próxima ação",
            "payment_platform": "Pagamento",
            "account_count": "Contas",
        },
    )


def portfolio(customers: pd.DataFrame) -> None:
    st.title("Minha carteira")
    data = active_portfolio(customers)
    selected_health = st.multiselect(
        "Saúde",
        list(HEALTH_LABELS.values()),
        default=list(HEALTH_LABELS.values()),
    )
    search = st.text_input("Buscar cliente")
    data = data[data["health_display"].isin(selected_health)]
    if search.strip():
        term = search.strip().casefold()
        searchable = (data["customer_name"] + " " + data["customer_id"] + " " + data["owner"]).str.casefold()
        data = data[searchable.str.contains(term, regex=False)]
    st.dataframe(
        data[["customer_id", "customer_name", "owner", "health_display", "last_platform_activity_date", "priority_display", "next_contact_date", "action_display"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "customer_id": "ID",
            "customer_name": "Cliente",
            "owner": "Responsável",
            "health_display": "Saúde",
            "last_platform_activity_date": st.column_config.DateColumn("Última atividade", format="DD/MM/YYYY"),
            "priority_display": "Prioridade",
            "next_contact_date": st.column_config.DateColumn("Próximo contato", format="DD/MM/YYYY"),
            "action_display": "Próxima ação",
        },
    )


def analytics(customers: pd.DataFrame) -> None:
    st.markdown('<div class="eyebrow">Saúde da carteira</div>', unsafe_allow_html=True)
    st.title("Analytics")
    active = active_portfolio(customers)
    tab_health, tab_risk, tab_churn = st.tabs(["Saúde", "Risco", "Churn"])
    with tab_health:
        counts = active["health_display"].value_counts().reindex(list(HEALTH_LABELS.values()), fill_value=0)
        st.bar_chart(counts)
        st.dataframe(active[["customer_name", "health_display", "last_platform_activity_date", "payment_platform", "account_count"]], use_container_width=True, hide_index=True)
    with tab_risk:
        counts = active["priority_display"].value_counts().reindex(["Alta", "Média", "Baixa"], fill_value=0)
        st.bar_chart(counts)
        st.dataframe(active.sort_values("contact_priority_score", ascending=False)[["customer_name", "priority_display", "health_display", "next_contact_date", "action_display"]], use_container_width=True, hide_index=True)
    with tab_churn:
        exits = customers[customers["customer_status"].isin(["Cancelled", "Desistencia"])].copy()
        metrics = st.columns(3)
        metrics[0].metric("Saídas", len(exits))
        metrics[1].metric("Cancelamentos", int((exits["customer_status"] == "Cancelled").sum()))
        metrics[2].metric("Desistências", int((exits["customer_status"] == "Desistencia").sum()))
        st.dataframe(exits[["customer_name", "entry_date", "cancellation_date", "cancellation_reason"]], use_container_width=True, hide_index=True)


def customers_page(customers: pd.DataFrame) -> None:
    st.markdown('<div class="eyebrow">Gestão da carteira</div>', unsafe_allow_html=True)
    st.title("Clientes")
    st.caption("Edite as linhas ou use a última linha vazia para cadastrar um cliente fictício.")

    editable = pd.DataFrame(
        {
            "ID": customers["customer_id"],
            "Cliente": customers["customer_name"],
            "Responsável": customers["owner"],
            "Status": customers["customer_status"].map(CUSTOMER_STATUS_LABELS),
            "Saúde": customers["platform_status"].map(HEALTH_LABELS),
            "Próximo contato": customers["next_contact_date"],
            "Último contato": customers["last_contact_date"],
            "Follow-ups": customers["follow_up_count"],
            "Renovação (dias)": customers["renewal_days"],
            "Ciclo": customers["plan_cycle"],
            "Pagamento": customers["payment_platform"],
            "Contas": customers["account_count"],
            "Última atividade": customers["last_platform_activity_date"],
            "Notas": customers["notes"],
        }
    )
    with st.form("demo_customer_editor"):
        edited = st.data_editor(
            editable,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=list(CUSTOMER_STATUS_VALUES),
                    required=True,
                ),
                "Saúde": st.column_config.SelectboxColumn(
                    "Saúde",
                    options=list(HEALTH_LABELS.values()),
                ),
                "Próximo contato": st.column_config.DateColumn("Próximo contato", format="DD/MM/YYYY"),
                "Último contato": st.column_config.DateColumn("Último contato", format="DD/MM/YYYY"),
                "Última atividade": st.column_config.DateColumn("Última atividade", format="DD/MM/YYYY"),
                "Follow-ups": st.column_config.NumberColumn("Follow-ups", min_value=0, step=1),
                "Renovação (dias)": st.column_config.NumberColumn("Renovação (dias)", min_value=0, step=1),
                "Contas": st.column_config.NumberColumn("Contas", min_value=0, step=1),
            },
        )
        save = st.form_submit_button("Aplicar alterações na demonstração", type="primary", use_container_width=True)

    if save:
        updated_rows = []
        health_values = {label: value for value, label in HEALTH_LABELS.items()}
        existing = {str(row["customer_id"]): row for _, row in customers.iterrows()}
        for position, row in edited.iterrows():
            name = str(row.get("Cliente") or "").strip()
            if not name:
                continue
            customer_id = str(row.get("ID") or "").strip() or f"DEMO-{position + 1:03d}"
            base = existing.get(customer_id, pd.Series(dtype=object)).to_dict()
            base.update(
                {
                    "customer_id": customer_id,
                    "customer_name": name,
                    "owner": str(row.get("Responsável") or "").strip(),
                    "customer_status": CUSTOMER_STATUS_VALUES.get(row.get("Status"), "Active"),
                    "platform_status": health_values.get(row.get("Saúde"), "Healthy"),
                    "next_contact_date": normalize_date(row.get("Próximo contato")),
                    "last_contact_date": normalize_date(row.get("Último contato")),
                    "follow_up_count": int(row.get("Follow-ups") or 0),
                    "renewal_days": None if pd.isna(row.get("Renovação (dias)")) else int(row.get("Renovação (dias)")),
                    "plan_cycle": str(row.get("Ciclo") or "Mensal"),
                    "payment_platform": str(row.get("Pagamento") or ""),
                    "account_count": int(row.get("Contas") or 0),
                    "last_platform_activity_date": normalize_date(row.get("Última atividade")),
                    "notes": str(row.get("Notas") or ""),
                    "contact_status": base.get("contact_status") or "Not contacted",
                    "response_status": base.get("response_status") or "Not applicable",
                    "entry_date": base.get("entry_date") or date.today(),
                    "cancellation_date": base.get("cancellation_date"),
                    "cancellation_reason": base.get("cancellation_reason"),
                    "is_internal": bool(base.get("is_internal", False)),
                }
            )
            updated_rows.append(base)
        st.session_state.demo_customers = pd.DataFrame(updated_rows)
        st.success("Dados da demonstração atualizados nesta sessão.")
        st.rerun()


if "demo_customers" not in st.session_state:
    st.session_state.demo_customers = build_demo_customers()
customers = st.session_state.demo_customers.copy()
with st.sidebar:
    st.markdown("### CS Operations Hub")
    st.caption("Versão Lite · demonstração")
    page = st.radio(
        "Navegação",
        ["▦ Visão geral", "▤ Minha carteira", "▥ Analytics", "♙ Clientes"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Restaurar dados da Demo", use_container_width=True):
        st.session_state.demo_customers = build_demo_customers()
        st.rerun()
    st.caption("Dados fictícios. Alterações válidas somente nesta sessão.")

st.markdown('<div class="demo-banner"><strong>Ambiente demonstrativo:</strong> os dados desta versão são fictícios e renovados automaticamente.</div>', unsafe_allow_html=True)

if page == "▦ Visão geral":
    overview(customers)
elif page == "▤ Minha carteira":
    portfolio(customers)
elif page == "▥ Analytics":
    analytics(customers)
else:
    customers_page(customers)
