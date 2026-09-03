from __future__ import annotations

from datetime import date
from html import escape

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
    [data-testid="stSidebar"] div[role="radiogroup"]{gap:5px}
    [data-testid="stSidebar"] div[role="radiogroup"] label{padding:9px 11px;border-radius:9px;border:1px solid transparent;transition:all .15s ease}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#fff;border-color:#e5e7eb}
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:#fff;border-color:#fecaca;box-shadow:0 2px 8px rgba(15,23,42,.05)}
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child{display:none}
    [data-testid="stMetric"]{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:12px 14px}
    .eyebrow{font-size:.76rem;text-transform:uppercase;letter-spacing:.1em;color:#c62828;font-weight:800}
    .demo-banner{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:10px 14px;margin-bottom:18px}
    .hero-title{font-size:2rem;font-weight:800;line-height:1.15;color:#111827;margin:.25rem 0 .35rem}
    .hero-copy{color:#6b7280;margin-bottom:1.25rem}
    .stat-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:16px 18px;min-height:104px}
    .stat-value{font-size:1.75rem;font-weight:800;line-height:1.1}
    .stat-label{font-size:.82rem;color:#6b7280;margin-top:7px}
    .stat-sub{font-size:.72rem;color:#9ca3af;margin-top:3px}
    .section-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin-bottom:1rem}
    .section-title{font-size:.9rem;font-weight:800;color:#374151;margin-bottom:14px}
    .bar-row{display:grid;grid-template-columns:minmax(105px,1.35fr) 2.5fr 28px;gap:10px;align-items:center;margin:10px 0;font-size:.78rem;color:#4b5563}
    .bar-track{height:8px;background:#f3f4f6;border-radius:999px;overflow:hidden}
    .bar-fill{height:100%;border-radius:999px}
    .risk-card{background:#fff;border:1px solid #fee2e2;border-left:4px solid #dc2626;border-radius:12px;padding:14px 16px;margin-bottom:10px}
    .risk-name{font-weight:750;color:#111827}
    .risk-meta{font-size:.78rem;color:#6b7280;margin-top:4px}
    .customer-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:15px 18px;margin-bottom:10px;transition:box-shadow .18s ease,border-color .18s ease}
    .customer-card:hover{box-shadow:0 5px 18px rgba(15,23,42,.07);border-color:#d1d5db}
    .customer-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:7px}
    .customer-name{font-weight:800;font-size:.94rem;color:#111827}
    .badge{border-radius:7px;padding:3px 8px;font-size:.69rem;font-weight:800;white-space:nowrap}
    .badge-active{background:#dcfce7;color:#15803d;border:1px solid #bbf7d0}
    .badge-cancelled{background:#fee2e2;color:#b91c1c;border:1px solid #fecaca}
    .badge-withdrawal{background:#fef3c7;color:#92400e;border:1px solid #fde68a}
    .badge-healthy{background:#dcfce7;color:#15803d}
    .badge-risk{background:#fef3c7;color:#92400e}
    .badge-critical{background:#fee2e2;color:#b91c1c}
    .badge-new{background:#ede9fe;color:#6d28d9}
    .customer-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:.76rem;color:#6b7280;line-height:1.55}
    .customer-note{font-size:.76rem;color:#4b5563;margin-top:7px;padding-top:7px;border-top:1px solid #f3f4f6}
    .customer-alert{font-size:.74rem;color:#b91c1c;margin-top:5px;font-weight:650}
    .portfolio-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:15px 18px;margin-bottom:10px}
    .portfolio-card.priority-high{border-left:4px solid #dc2626}
    .portfolio-card.priority-medium{border-left:4px solid #f59e0b}
    .portfolio-card.priority-low{border-left:4px solid #16a34a}
    .action-line{margin-top:8px;padding:7px 10px;border-radius:8px;background:#f8fafc;color:#334155;font-size:.76rem;font-weight:650}
    .analytics-summary{background:linear-gradient(135deg,#fff 0%,#f8fafc 100%);border:1px solid #e5e7eb;border-radius:14px;padding:18px}
    .analytics-summary strong{display:block;color:#111827;font-size:.9rem;margin-bottom:5px}
    .analytics-summary span{color:#6b7280;font-size:.77rem}
    @media (max-width:700px){.hero-title{font-size:1.55rem}.stat-card{min-height:94px}.bar-row{grid-template-columns:95px 1fr 24px}}
    </style>
    """,
    unsafe_allow_html=True,
)


def stat_card(label: str, value: str | int, color: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{color}">{escape(str(value))}</div>
            <div class="stat-label">{escape(label)}</div>
            <div class="stat-sub">{escape(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def distribution_card(title: str, values: pd.Series, color: str) -> None:
    values = values[values > 0]
    rows = []
    maximum = int(values.max()) if not values.empty else 0
    for label, value in values.items():
        width = 0 if maximum == 0 else round(int(value) / maximum * 100)
        rows.append(
            '<div class="bar-row">'
            f'<span title="{escape(str(label))}">{escape(str(label))}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width}%;background:{color}"></div></div>'
            f'<strong>{int(value)}</strong></div>'
        )
    content = "".join(rows) or '<span style="color:#9ca3af;font-size:.8rem">Sem dados nesta categoria.</span>'
    st.markdown(
        f'<div class="section-card"><div class="section-title">{escape(title)}</div>{content}</div>',
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
    exits = customers[customers["customer_status"].isin(["Cancelled", "Desistencia"])].copy()
    health = active["platform_status"].value_counts()
    attention_statuses = ["AtRisk", "Dormant", "NeverActivated"]
    attention = active[active["platform_status"].isin(attention_statuses)].copy()
    due = active["next_contact_date"].apply(normalize_date)
    due_today = int(due.apply(lambda value: value is not None and value <= date.today()).sum())

    st.markdown('<div class="eyebrow">Visão executiva da operação</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Saúde da carteira em um só lugar</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Indicadores, riscos e próximas ações para priorizar o relacionamento com clientes.</div>',
        unsafe_allow_html=True,
    )

    cards = st.columns(6)
    with cards[0]:
        stat_card("Clientes ativos", len(active), "#16a34a", "carteira atual")
    with cards[1]:
        stat_card("Saídas registradas", len(exits), "#dc2626", "histórico da Demo")
    with cards[2]:
        stat_card("Precisam de atenção", len(attention), "#f59e0b", "ativos com sinal de risco")
    with cards[3]:
        stat_card("Nunca ativaram", int(health.get("NeverActivated", 0)), "#7c3aed", "onboarding pendente")
    with cards[4]:
        stat_card("Contatos vencidos", due_today, "#2563eb", "contato até hoje")
    with cards[5]:
        stat_card("Total da base", len(customers), "#111827", "ativos e históricos")

    left, right = st.columns(2)
    health_distribution = health.rename(index=HEALTH_LABELS).reindex(list(HEALTH_LABELS.values()), fill_value=0)
    exit_reasons = exits["cancellation_reason"].fillna("Motivo não informado").value_counts()
    with left:
        distribution_card("Distribuição da saúde dos clientes ativos", health_distribution, "#2563eb")
    with right:
        distribution_card("Motivos das saídas registradas", exit_reasons, "#dc2626")

    health_weight = {"NeverActivated": 4, "Dormant": 3, "AtRisk": 2, "Healthy": 0}
    active["daily_score"] = active["contact_priority_score"] + active["platform_status"].map(health_weight).fillna(0) * 25
    queue = active.sort_values("daily_score", ascending=False)
    st.markdown("### 🚨 Clientes que precisam de ação")
    st.caption("Lista ordenada pela combinação entre saúde, contato pendente e proximidade da renovação.")
    priority_queue = queue[queue["platform_status"].isin(attention_statuses)]
    if priority_queue.empty:
        st.success("Nenhum cliente com alerta operacional no momento.")
    else:
        for _, customer in priority_queue.iterrows():
            next_contact = normalize_date(customer.get("next_contact_date"))
            next_contact_label = next_contact.strftime("%d/%m/%Y") if next_contact else "não agendado"
            st.markdown(
                f"""
                <div class="risk-card">
                    <div class="risk-name">{escape(str(customer['customer_name']))}</div>
                    <div class="risk-meta">
                        {escape(str(customer['health_display']))} · Prioridade {escape(str(customer['priority_display']).lower())}
                        · {escape(str(customer['action_display']))} · Próximo contato: {next_contact_label}
                        · Responsável: {escape(str(customer['owner']))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def portfolio(customers: pd.DataFrame) -> None:
    st.markdown('<div class="eyebrow">Acompanhamento operacional</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Minha carteira</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Encontre rapidamente quem precisa de contato e qual é a próxima ação recomendada.</div>',
        unsafe_allow_html=True,
    )
    data = active_portfolio(customers)
    summary = st.columns(4)
    with summary[0]:
        stat_card("Clientes ativos", len(data), "#16a34a")
    with summary[1]:
        stat_card("Prioridade alta", int((data["contact_priority"] == "High").sum()), "#dc2626")
    with summary[2]:
        stat_card("Contato até hoje", int(data["next_contact_date"].apply(normalize_date).apply(lambda value: value is not None and value <= date.today()).sum()), "#2563eb")
    with summary[3]:
        stat_card("Renovação em 30 dias", int(data["renewal_days"].apply(lambda value: pd.notna(value) and int(value) <= 30).sum()), "#7c3aed")

    search_col, health_col, priority_col = st.columns([2, 1, 1])
    with search_col:
        search = st.text_input("Buscar cliente", placeholder="Nome, ID ou responsável...", key="portfolio_search")
    with health_col:
        selected_health = st.multiselect(
            "Saúde",
            list(HEALTH_LABELS.values()),
            default=list(HEALTH_LABELS.values()),
        )
    with priority_col:
        selected_priority = st.selectbox("Prioridade", ["Todas", "Alta", "Média", "Baixa"])

    data = data[data["health_display"].isin(selected_health)]
    if selected_priority != "Todas":
        data = data[data["priority_display"] == selected_priority]
    if search.strip():
        term = search.strip().casefold()
        searchable = (data["customer_name"] + " " + data["customer_id"] + " " + data["owner"]).str.casefold()
        data = data[searchable.str.contains(term, regex=False)]
    data = data.sort_values("contact_priority_score", ascending=False)
    st.caption(f"{len(data)} cliente{'s' if len(data) != 1 else ''} na seleção")
    if data.empty:
        st.info("Nenhum cliente encontrado com esses filtros.")
    else:
        for _, customer in data.iterrows():
            health = str(customer.get("platform_status") or "Healthy")
            health_class = {
                "Healthy": "badge-healthy", "AtRisk": "badge-risk",
                "Dormant": "badge-critical", "NeverActivated": "badge-new",
            }.get(health, "badge-healthy")
            priority = str(customer.get("contact_priority") or "Low").lower()
            next_contact = normalize_date(customer.get("next_contact_date"))
            contact_label = next_contact.strftime("%d/%m/%Y") if next_contact else "não agendado"
            last_activity = normalize_date(customer.get("last_platform_activity_date"))
            activity_label = last_activity.strftime("%d/%m/%Y") if last_activity else "sem atividade"
            card = (
                f'<div class="portfolio-card priority-{escape(priority)}">'
                '<div class="customer-head">'
                f'<span class="customer-name">{escape(str(customer["customer_name"]))}</span>'
                f'<span class="badge {health_class}">{escape(str(customer["health_display"]))}</span>'
                f'<span class="badge badge-{"critical" if priority == "high" else "risk" if priority == "medium" else "healthy"}">Prioridade {escape(str(customer["priority_display"]).lower())}</span>'
                '</div><div class="customer-meta">'
                f'<span>♙ {escape(str(customer["owner"]))}</span>'
                f'<span>☎ Próximo contato: {escape(contact_label)}</span>'
                f'<span>◷ Última atividade: {escape(activity_label)}</span>'
                f'<span>💳 {escape(str(customer["payment_platform"]))}</span>'
                f'<span>▦ {int(customer["account_count"])} conta{"s" if int(customer["account_count"]) != 1 else ""}</span>'
                '</div>'
                f'<div class="action-line">→ {escape(str(customer["action_display"]))}</div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)


def analytics(customers: pd.DataFrame) -> None:
    st.markdown('<div class="eyebrow">Saúde da carteira</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Leitura gerencial da saúde, dos riscos e das saídas registradas na carteira.</div>',
        unsafe_allow_html=True,
    )
    active = active_portfolio(customers)
    exits = customers[customers["customer_status"].isin(["Cancelled", "Desistencia"])].copy()
    top = st.columns(4)
    with top[0]:
        stat_card("Base analisada", len(customers), "#111827", "ativos e históricos")
    with top[1]:
        stat_card("Saúde estável", int((active["platform_status"] == "Healthy").sum()), "#16a34a", "clientes ativos")
    with top[2]:
        stat_card("Prioridade alta", int((active["contact_priority"] == "High").sum()), "#dc2626", "ação recomendada")
    with top[3]:
        stat_card("Saídas", len(exits), "#7c3aed", "cancelamentos e desistências")

    tab_health, tab_risk, tab_churn = st.tabs(["Saúde", "Risco", "Churn"])
    with tab_health:
        counts = active["health_display"].value_counts().reindex(list(HEALTH_LABELS.values()), fill_value=0)
        left, right = st.columns([1, 1.35])
        with left:
            distribution_card("Distribuição da saúde", counts, "#2563eb")
        with right:
            st.markdown('<div class="analytics-summary"><strong>Como interpretar</strong><span>Clientes dormentes, em risco ou que nunca ativaram devem alimentar a fila operacional da carteira.</span></div>', unsafe_allow_html=True)
        st.dataframe(active[["customer_name", "health_display", "last_platform_activity_date", "payment_platform", "account_count"]], use_container_width=True, hide_index=True)
    with tab_risk:
        counts = active["priority_display"].value_counts().reindex(["Alta", "Média", "Baixa"], fill_value=0)
        left, right = st.columns([1, 1.35])
        with left:
            distribution_card("Distribuição das prioridades", counts, "#f59e0b")
        with right:
            st.markdown('<div class="analytics-summary"><strong>Critério operacional</strong><span>A prioridade combina contatos pendentes, ausência de resposta e proximidade da renovação.</span></div>', unsafe_allow_html=True)
        st.dataframe(active.sort_values("contact_priority_score", ascending=False)[["customer_name", "priority_display", "health_display", "next_contact_date", "action_display"]], use_container_width=True, hide_index=True)
    with tab_churn:
        metrics = st.columns(2)
        with metrics[0]:
            stat_card("Cancelamentos", int((exits["customer_status"] == "Cancelled").sum()), "#dc2626")
        with metrics[1]:
            stat_card("Desistências", int((exits["customer_status"] == "Desistencia").sum()), "#f59e0b")
        distribution_card("Motivos das saídas", exits["cancellation_reason"].fillna("Motivo não informado").value_counts(), "#dc2626")
        st.dataframe(exits[["customer_name", "entry_date", "cancellation_date", "cancellation_reason"]], use_container_width=True, hide_index=True)


def customer_card(customer: pd.Series) -> None:
    status = str(customer.get("customer_status") or "Active")
    health = str(customer.get("platform_status") or "Healthy")
    status_class = {
        "Active": "badge-active",
        "Cancelled": "badge-cancelled",
        "Desistencia": "badge-withdrawal",
    }.get(status, "badge-active")
    health_class = {
        "Healthy": "badge-healthy",
        "AtRisk": "badge-risk",
        "Dormant": "badge-critical",
        "NeverActivated": "badge-new",
    }.get(health, "badge-healthy")
    entry_date = normalize_date(customer.get("entry_date"))
    next_contact = normalize_date(customer.get("next_contact_date"))
    cancellation_date = normalize_date(customer.get("cancellation_date"))
    entry_label = entry_date.strftime("%d/%m/%Y") if entry_date else "não informada"
    contact_label = next_contact.strftime("%d/%m/%Y") if next_contact else "não agendado"
    plan = str(customer.get("plan_cycle") or "Não informado")
    payment = str(customer.get("payment_platform") or "Não informado")
    accounts = int(customer.get("account_count") or 0)
    owner = str(customer.get("owner") or "Não definido")
    notes = str(customer.get("notes") or "").strip()
    cancellation_reason = str(customer.get("cancellation_reason") or "").strip()

    exit_detail = ""
    if status != "Active":
        exit_date_label = cancellation_date.strftime("%d/%m/%Y") if cancellation_date else "não informada"
        exit_detail = f'<span>📤 Saída: {escape(exit_date_label)}</span>'

    note_html = f'<div class="customer-note">📝 {escape(notes)}</div>' if notes else ""
    alert_html = (
        f'<div class="customer-alert">⚠ {escape(cancellation_reason)}</div>'
        if cancellation_reason
        else ""
    )
    card_html = (
        '<div class="customer-card">'
        '<div class="customer-head">'
        f'<span class="customer-name">{escape(str(customer.get("customer_name") or "Cliente sem nome"))}</span>'
        f'<span class="badge {status_class}">{escape(CUSTOMER_STATUS_LABELS.get(status, status))}</span>'
        f'<span class="badge {health_class}">{escape(HEALTH_LABELS.get(health, health))}</span>'
        '</div><div class="customer-meta">'
        f'<span>♙ {escape(owner)}</span>'
        f'<span>💳 {escape(plan)}</span>'
        f'<span>🏦 {escape(payment)}</span>'
        f'<span>📅 Entrada: {escape(entry_label)}</span>'
        f'<span>☎ Próximo contato: {escape(contact_label)}</span>'
        f'<span>▦ {accounts} conta{"s" if accounts != 1 else ""}</span>'
        f'{exit_detail}</div>{note_html}{alert_html}</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def customers_page(customers: pd.DataFrame) -> None:
    st.markdown('<div class="eyebrow">Gestão da carteira</div>', unsafe_allow_html=True)
    st.title("Clientes")
    st.caption("Consulte a carteira em cartões ou altere os dados fictícios na tabela editável.")

    view_tab, edit_tab = st.tabs(["▦ Visualização", "✎ Editar dados"])

    with view_tab:
        search_col, status_col, health_col = st.columns([2.2, 1, 1])
        with search_col:
            search = st.text_input(
                "Buscar cliente ou responsável",
                placeholder="Digite um nome...",
                key="customer_card_search",
            )
        with status_col:
            status_filter = st.selectbox(
                "Status",
                ["Todos", *CUSTOMER_STATUS_LABELS.values()],
                key="customer_card_status",
            )
        with health_col:
            health_filter = st.selectbox(
                "Saúde",
                ["Todas", *HEALTH_LABELS.values()],
                key="customer_card_health",
            )

        visible = customers.copy()
        if search.strip():
            term = search.strip().casefold()
            searchable = (
                visible["customer_name"].fillna("").astype(str)
                + " "
                + visible["owner"].fillna("").astype(str)
            ).str.casefold()
            visible = visible[searchable.str.contains(term, regex=False)]
        if status_filter != "Todos":
            status_value = CUSTOMER_STATUS_VALUES[status_filter]
            visible = visible[visible["customer_status"] == status_value]
        if health_filter != "Todas":
            health_values = {label: value for value, label in HEALTH_LABELS.items()}
            visible = visible[visible["platform_status"] == health_values[health_filter]]

        st.caption(f"{len(visible)} cliente{'s' if len(visible) != 1 else ''} encontrado{'s' if len(visible) != 1 else ''}")
        if visible.empty:
            st.info("Nenhum cliente encontrado com esses filtros.")
        else:
            status_order = {"Active": 0, "Cancelled": 1, "Desistencia": 2}
            health_order = {"Dormant": 0, "AtRisk": 1, "NeverActivated": 2, "Healthy": 3}
            ordered = visible.assign(
                _status_order=visible["customer_status"].map(status_order).fillna(9),
                _health_order=visible["platform_status"].map(health_order).fillna(9),
            ).sort_values(["_status_order", "_health_order", "customer_name"])
            for _, customer in ordered.iterrows():
                customer_card(customer)

    with edit_tab:
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
