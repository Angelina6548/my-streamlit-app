import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ---------- Настройки страницы ----------
st.set_page_config(
    page_title="Семейный бюджет",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Стили (пастельные зелёно-серо-чёрные) ----------
st.markdown("""
<style>
    .main { background-color: #f4f6f4; }
    h1, h2, h3 { color: #2f3e34; }
    .metric-card {
        background: #e8efe8;
        padding: 18px;
        border-radius: 12px;
        border-left: 5px solid #7fa88a;
        margin-bottom: 12px;
    }
    .metric-title { color: #5c6b60; font-size: 14px; }
    .metric-value { color: #2f3e34; font-size: 26px; font-weight: bold; }
    .stButton>button {
        background-color: #7fa88a; color: white;
        border-radius: 8px; border: none; padding: 8px 20px;
    }
    .stButton>button:hover { background-color: #6b9276; }
</style>
""", unsafe_allow_html=True)

# ---------- Подключение к Google Sheets ----------
conn = st.connection("gsheets", type=GSheetsConnection)
SPREADSHEET_URL = st.secrets["connections.gsheets"]["spreadsheet"]
def load_sheet(name):
    return conn.read(spreadsheet=SPREADSHEET_URL, worksheet=name, ttl=0)

def save_sheet(df, name):
    conn.update(spreadsheet=SPREADSHEET_URL, worksheet=name, data=df)

# ---------- Заголовок ----------
st.title("💰 Семейный бюджет")
st.caption("Приложение для совместного учёта финансов")

# ---------- Боковое меню ----------
menu = st.sidebar.radio(
    "Разделы:",
    ["📊 Обзор", "💸 Транзакции", "🎯 Копилки", "🏠 Кредиты", "⚙️ Настройки"]
)

# ==================================================================
# РАЗДЕЛ 1: ОБЗОР
# ==================================================================
if menu == "📊 Обзор":
    st.header("📊 Обзор бюджета")

    try:
        tx = load_sheet("Транзакции")
        tx = tx.dropna(how="all")

        if len(tx) > 0:
            tx["Сумма"] = pd.to_numeric(tx["Сумма"], errors="coerce").fillna(0)

            income = tx[tx["Тип"] == "Доход"]["Сумма"].sum()
            expense = tx[tx["Тип"] == "Расход"]["Сумма"].sum()
            balance = income - expense

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="metric-card"><div class="metric-title">💵 Доходы</div><div class="metric-value">{income:,.0f} ₽</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><div class="metric-title">💸 Расходы</div><div class="metric-value">{expense:,.0f} ₽</div></div>', unsafe_allow_html=True)
            with col3:
                color = "#7fa88a" if balance >= 0 else "#c97a7a"
                st.markdown(f'<div class="metric-card" style="border-left-color:{color};"><div class="metric-title">⚖️ Остаток</div><div class="metric-value" style="color:{color};">{balance:,.0f} ₽</div></div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("Расходы по категориям")
            exp_only = tx[tx["Тип"] == "Расход"]
            if len(exp_only) > 0:
                by_cat = exp_only.groupby("Категория")["Сумма"].sum().sort_values(ascending=False)
                st.bar_chart(by_cat)
            else:
                st.info("Пока нет расходов для отображения.")
        else:
            st.info("Пока нет транзакций. Добавьте первую во вкладке «💸 Транзакции».")
    except Exception as e:
        st.error("Не удалось загрузить данные. Проверьте подключение к Google Sheets.")
        st.code(str(e))

# ==================================================================
# РАЗДЕЛ 2: ТРАНЗАКЦИИ
# ==================================================================
elif menu == "💸 Транзакции":
    st.header("💸 Транзакции")
    st.write("Быстрый ввод одной строкой. Формат:")
    st.code("-1500 Еда обед в кафе\n+80000 Зарплата\n-3000 Копилка Свадьба")
    st.caption("Знак `-` — расход, `+` — доход. После суммы — категория, дальше — комментарий.")

    who = st.selectbox("Кто вносит:", ["Ангелина", "Партнёр"])
    quick = st.text_input("Быстрый ввод:", placeholder="-1500 Еда обед")

    if st.button("➕ Добавить транзакцию"):
        if quick.strip():
            parts = quick.strip().split(maxsplit=2)
            sign = parts[0][0]
            try:
                amount = float(parts[0].replace(",", "."))
                category = parts[1] if len(parts) > 1 else "Прочее"
                comment = parts[2] if len(parts) > 2 else ""
                tx_type = "Доход" if sign == "+" else "Расход"

                new_row = pd.DataFrame([{
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Сумма": amount,
                    "Категория": category,
                    "Комментарий": comment,
                    "Кто_внёс": who,
                    "Тип": tx_type
                }])

                try:
                    existing = load_sheet("Транзакции").dropna(how="all")
                    updated = pd.concat([existing, new_row], ignore_index=True)
                except Exception:
                    updated = new_row

                save_sheet(updated, "Транзакции")
                st.success(f"✅ Добавлено: {quick}")
                st.rerun()
            except Exception as e:
                st.error(f"Не удалось разобрать строку: {e}")
        else:
            st.warning("Введите строку для добавления.")

    st.divider()
    st.subheader("Последние транзакции")
    try:
        tx = load_sheet("Транзакции").dropna(how="all")
        if len(tx) > 0:
            st.dataframe(tx.tail(20).iloc[::-1], use_container_width=True)
        else:
            st.info("Пока нет транзакций.")
    except Exception as e:
        st.error("Не удалось загрузить транзакции.")
        st.code(str(e))

# ==================================================================
# РАЗДЕЛ 3: КОПИЛКИ
# ==================================================================
elif menu == "🎯 Копилки":
    st.header("🎯 Копилки и желания")

    try:
        goals = load_sheet("Копилки").dropna(how="all")

        if len(goals) > 0:
            for i, row in goals.iterrows():
                target = float(row["Целевая_сумма"]) if pd.notna(row["Целевая_сумма"]) else 0
                saved = float(row["Накоплено"]) if pd.notna(row["Накоплено"]) else 0
                progress = saved / target if target > 0 else 0

                with st.container():
                    st.markdown(f"### {row['Название_цели']}")
                    st.progress(min(progress, 1.0))
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Накоплено", f"{saved:,.0f} ₽")
                    c2.metric("Цель", f"{target:,.0f} ₽")
                    c3.metric("Осталось", f"{max(target - saved, 0):,.0f} ₽")

                    add = st.number_input(
                        f"Пополнить «{row['Название_цели']}»:",
                        min_value=0.0, step=100.0, key=f"add_{i}"
                    )
                    if st.button(f"➕ Внести в «{row['Название_цели']}»", key=f"btn_{i}"):
                        if add > 0:
                            goals.at[i, "Накоплено"] = saved + add
                            save_sheet(goals, "Копилки")
                            st.success(f"Добавлено {add:,.0f} ₽")
                            st.rerun()
                    st.divider()
        else:
            st.info("Пока нет копилок. Добавьте их в листе «Копилки» Google-таблицы.")
    except Exception as e:
        st.error("Не удалось загрузить копилки.")
        st.code(str(e))

# ==================================================================
# РАЗДЕЛ 4: КРЕДИТЫ
# ==================================================================
elif menu == "🏠 Кредиты":
    st.header("🏠 Кредиты и ипотека")

    try:
        credits = load_sheet("Кредиты").dropna(how="all")

        if len(credits) > 0:
            for i, row in credits.iterrows():
                total = float(row["Общая_сумма"]) if pd.notna(row["Общая_сумма"]) else 0
                paid = float(row["Внесено"]) if pd.notna(row["Внесено"]) else 0
                left = max(total - paid, 0)
                progress = paid / total if total > 0 else 0

                st.markdown(f"### {row['Название']}")
                st.progress(min(progress, 1.0))
                c1, c2, c3 = st.columns(3)
                c1.metric("Выплачено", f"{paid:,.0f} ₽")
                c2.metric("Осталось", f"{left:,.0f} ₽")
                c3.metric("Ежемесячный платёж", f"{row['Ежемесячный_платёж']:,.0f} ₽")

                payment = st.number_input(
                    f"Внести платёж по «{row['Название']}»:",
                    min_value=0.0, step=1000.0, key=f"pay_{i}"
                )
                if st.button(f"💳 Внести платёж по «{row['Название']}»", key=f"cbtn_{i}"):
                    if payment > 0:
                        credits.at[i, "Внесено"] = paid + payment
                        credits.at[i, "Остаток"] = max(total - (paid + payment), 0)
                        save_sheet(credits, "Кредиты")
                        st.success(f"Внесено {payment:,.0f} ₽")
                        st.rerun()
                st.divider()
        else:
            st.info("Пока нет кредитов. Добавьте их в листе «Кредиты» Google-таблицы.")
    except Exception as e:
        st.error("Не удалось загрузить кредиты.")
        st.code(str(e))

# ==================================================================
# РАЗДЕЛ 5: НАСТРОЙКИ
# ==================================================================
elif menu == "⚙️ Настройки":
    st.header("⚙️ Настройки")

    st.subheader("Категории")
    try:
        cats = load_sheet("Категории").dropna(how="all")
        if len(cats) > 0:
            st.write("Текущие категории:")
            for c in cats["Категория"].tolist():
                st.write(f"• {c}")
        else:
            st.info("Список категорий пуст.")

        new_cat = st.text_input("Новая категория:")
        if st.button("➕ Добавить категорию"):
            if new_cat.strip():
                new_row = pd.DataFrame([{"Категория": new_cat.strip()}])
                try:
                    existing = load_sheet("Категории").dropna(how="all")
                    updated = pd.concat([existing, new_row], ignore_index=True)
                except Exception:
                    updated = new_row
                save_sheet(updated, "Категории")
                st.success(f"Добавлено: {new_cat}")
                st.rerun()

        del_cat = st.selectbox("Удалить категорию:", [""] + (cats["Категория"].tolist() if len(cats) > 0 else []))
        if st.button("🗑 Удалить категорию"):
            if del_cat:
                cats = cats[cats["Категория"] != del_cat]
                save_sheet(cats, "Категории")
                st.success(f"Удалено: {del_cat}")
                st.rerun()
    except Exception as e:
        st.error("Не удалось загрузить категории.")
        st.code(str(e))

    st.divider()
    st.subheader("О приложении")
    st.write("Семейный бюджет · Версия 1.0")
    st.write("Данные хранятся в вашей Google-таблице.")
