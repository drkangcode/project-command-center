import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime, timedelta, date
import json
import calendar
import streamlit.components.v1 as components

# --- 1. 基础配置 ---
st.set_page_config(
    page_title="Personal Command Center",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded" 
)

# --- 2. 状态初始化 ---
if "current_view" not in st.session_state: st.session_state.current_view = "dashboard"
if "selected_task_index" not in st.session_state: st.session_state.selected_task_index = None

# --- 3. 样式优化 ---
st.markdown("""
    <style>
    /* 1. 全局字体: 18px */
    html, body, [class*="css"], .stDataFrame, .stMarkdown, .stText, input, textarea, label, div {
        font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 18px !important; 
        color: #1F2937;
    }

    /* 2. 标题特调 */
    h1 { font-size: 32px !important; font-weight: 900 !important; padding: 5px 0; }
    h2 { font-size: 24px !important; font-weight: 700 !important; }
    h3 { font-size: 20px !important; font-weight: 700 !important; }
    
    /* 3. 左侧侧边栏宽度 */
    [data-testid="stSidebar"] { min-width: 480px !important; max-width: 480px !important; }

    /* 4. 容器卡片 */
    .stApp { background-color: #F3F4F6; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* 5. 日历美化 */
    .calendar-table { width: 100%; border-collapse: separate; border-spacing: 2px; font-family: "Segoe UI", sans-serif; margin-top: 5px;}
    .calendar-table th { color: #6B7280; font-size: 14px; padding: 5px; font-weight: 600; }
    .calendar-table td { 
        text-align: center; padding: 8px; font-size: 16px; color: #374151; 
        border-radius: 8px; border: 1px solid transparent;
    }
    .calendar-table td:nth-child(6), .calendar-table td:nth-child(7) {
        background-color: #FFF0F5; color: #C71585; 
    }
    .calendar-table .today { 
        background: #2563EB !important; color: white !important; font-weight: 800; 
        box-shadow: 0 2px 8px rgba(37,99,235,0.4); 
    }
    
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 数据管理 ---
DATA_FILE = "life_data.csv"
LOG_FILE = "project_logs.csv"

CATEGORY_MAP = {"学术": "STUDY", "大模型": "LLM", "工作": "WORK", "兴趣": "LIFE"}
CATEGORY_LIST = list(CATEGORY_MAP.keys())

def get_data():
    cols = ["任务名称", "类别", "重要性(1-10)", "紧急性(1-10)", "当前进度(%)", "状态", "开始时间", "截止日期", "备注", "任务分解JSON", "专属笔记", "项目编号"]
    if not os.path.exists(DATA_FILE): return pd.DataFrame(columns=cols)
    try: df = pd.read_csv(DATA_FILE)
    except: return pd.DataFrame(columns=cols)
    for col in cols: 
        if col not in df.columns: df[col] = ""
    
    df["开始时间"] = pd.to_datetime(df["开始时间"], errors='coerce').fillna(pd.Timestamp.now()).dt.date
    df["截止日期"] = pd.to_datetime(df["截止日期"], errors='coerce').fillna(pd.Timestamp.now()+timedelta(7)).dt.date
    return df

def save_data(new_df): new_df.to_csv(DATA_FILE, index=False)

def get_logs():
    cols = ["日期", "项目", "子任务", "内容", "贡献进度"]
    if not os.path.exists(LOG_FILE): return pd.DataFrame(columns=cols)
    return pd.read_csv(LOG_FILE)

def save_log_entry(date_str, project, subtask, content, prog_incr):
    new = pd.DataFrame([[date_str, project, subtask, content, prog_incr]], columns=["日期", "项目", "子任务", "内容", "贡献进度"])
    if os.path.exists(LOG_FILE): new.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else: new.to_csv(LOG_FILE, index=False)

def generate_pid(df, category):
    prefix = CATEGORY_MAP.get(category, "PROJ")
    existing = df[df["项目编号"].str.startswith(prefix, na=False)]
    if existing.empty: next_num = 1
    else:
        try:
            max_id = existing["项目编号"].str.extract(r'(\d+)').astype(float).max().iloc[0]
            next_num = int(max_id) + 1 if not pd.isna(max_id) else 1
        except: next_num = len(existing) + 1
    return f"{prefix}-{next_num:02d}"

# --- 5. 组件 ---
def render_calendar():
    now = datetime.now()
    year, month = now.year, now.month
    cal = calendar.monthcalendar(year, month)
    html = f"""
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding:0 5px;'>
        <span style='font-size:18px; font-weight:800; color:#111827;'>{year}年 {month}月</span>
        <span style='font-size:12px; color:#6B7280; background:#E5E7EB; padding:3px 8px; border-radius:10px;'>今天: {now.day}号</span>
    </div>
    """
    html += "<table class='calendar-table'><thead><tr>"
    for day in ["一","二","三","四","五","六","日"]: html += f"<th>{day}</th>"
    html += "</tr></thead><tbody>"
    for week in cal:
        html += "<tr>"
        for i, day in enumerate(week):
            if day == 0: html += "<td></td>"
            else:
                cls = "class='today'" if day == now.day else ""
                html += f"<td {cls}>{day}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def live_clock_component():
    return components.html(
        """
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body { margin: 0; padding: 0; background: transparent; text-align: right; font-family: -apple-system, sans-serif; overflow: hidden; }
            .time { font-size: 64px; font-weight: 900; color: #111; line-height: 1.1; letter-spacing: -2px; }
            .date { font-size: 22px; color: #4B5563; font-weight: 700; margin-top: 5px; }
        </style>
        </head>
        <body>
            <div class="time" id="time">--:--</div>
            <div class="date" id="date">...</div>
            <script>
                function update() {
                    const now = new Date();
                    document.getElementById('time').innerText = now.toLocaleTimeString('en-GB', {hour12: false, hour:'2-digit', minute:'2-digit'});
                    document.getElementById('date').innerText = now.toLocaleDateString('zh-CN', {year:'numeric', month:'long', day:'numeric', weekday:'long'});
                }
                setInterval(update, 1000); update();
            </script>
        </body>
        </html>
        """, height=140
    )

# --- 6. 左侧侧边栏 ---
with st.sidebar:
    st.title("➕ 新建任务")
    
    with st.form("add_task_form"):
        nm = st.text_input("任务名称", placeholder="例如：ICIS论文投稿")
        cat = st.selectbox("分类", CATEGORY_LIST)
        
        df_preview = get_data()
        auto_pid = generate_pid(df_preview, cat)
        st.info(f"🆔 ID: **{auto_pid}**")
        pid_hidden = st.text_input("PID", value=auto_pid, disabled=True, label_visibility="collapsed")

        d1, d2 = st.columns(2)
        s_d = d1.date_input("开始", value=datetime.now())
        e_d = d2.date_input("截止", value=datetime.now()+timedelta(days=7))
        
        c1, c2 = st.columns(2)
        imp = c1.slider("重要性", 1, 10, 5)
        urg = c2.slider("紧急性", 1, 10, 5)
        
        st.write("---")
        st.write("**子任务分解**")
        
        subs = st.data_editor(
            pd.DataFrame({"子任务名称":[""]*5, "权重":[0]*5}), 
            column_config={
                "子任务名称": st.column_config.TextColumn(width="medium"),
                "权重": st.column_config.NumberColumn("权重%", width="small", min_value=0, max_value=100)
            },
            num_rows="dynamic", use_container_width=True
        )
        
        total_w = subs["权重"].sum()
        if total_w == 100: st.success(f"📊 总权重: {total_w}% (完美)")
        elif total_w < 100: st.warning(f"📊 总权重: {total_w}% (还差 {100-total_w}%)")
        else: st.error(f"📊 总权重: {total_w}% (超出了 {total_w-100}%)")
        
        if st.form_submit_button("🚀 立即创建", type="primary"):
            if nm:
                js = []
                valid = subs[subs["子任务名称"].str.strip() != ""]
                for idx, row in valid.iterrows():
                    sub_id = f"{auto_pid}-{idx+1:02d}"
                    js.append({"id": sub_id, "name": row["子任务名称"], "weight": int(row["权重"]), "done": False})
                
                df_curr = get_data()
                final_pid = generate_pid(df_curr, cat)
                new_row = pd.DataFrame({
                    "任务名称": [nm], "类别": [cat], "重要性(1-10)": [imp], "紧急性(1-10)": [urg],
                    "当前进度(%)": [0], "状态": ["未开始"],
                    "开始时间": [s_d], "截止日期": [e_d],
                    "项目编号": [final_pid], 
                    "备注": [""], "任务分解JSON": [json.dumps(js)], "专属笔记": [""]
                })
                save_data(pd.concat([df_curr, new_row], ignore_index=True))
                st.toast(f"✅ 任务 {final_pid} 已创建")
                time.sleep(0.5)
                st.rerun()

# --- 7. 核心布局 ---
col_main, col_right = st.columns([3.5, 1], gap="medium")

# === 中间主控区 ===
with col_main:
    # 顶部区域
    c_h, c_clk = st.columns([1.5, 1])
    c_h.title("🚀 控制中心")
    
    # 搜索逻辑
    search_query = c_h.text_input("🔍 全局搜索 (任务名/ID/子任务/类别)", placeholder="输入关键字...")
    
    with c_clk:
        live_clock_component()

    df = get_data()
    
    # 搜索执行
    if search_query:
        mask = (
            df["任务名称"].astype(str).str.contains(search_query, case=False, na=False) |
            df["项目编号"].astype(str).str.contains(search_query, case=False, na=False) |
            df["类别"].astype(str).str.contains(search_query, case=False, na=False) |
            df["任务分解JSON"].astype(str).str.contains(search_query, case=False, na=False)
        )
        search_results = df[mask]
        
        if not search_results.empty:
            st.success(f"🔍 找到 {len(search_results)} 个匹配项，**点击下方表格选中行，即可跳转详情**：")
            
            search_event = st.dataframe(
                search_results[["项目编号", "任务名称", "类别", "状态", "截止日期"]],
                use_container_width=True,
                selection_mode="single-row", 
                on_select="rerun",
                hide_index=True
            )
            
            if len(search_event.selection.rows) > 0:
                selected_display_index = search_event.selection.rows[0]
                real_index = search_results.index[selected_display_index]
                st.session_state.selected_task_index = real_index
                st.session_state.current_view = "detail"
                st.rerun()
        else:
            st.warning(f"🤔 未找到包含 '{search_query}' 的任务")

    # 如果有搜索，过滤下方视图
    if search_query:
        df = df[mask]

    if st.session_state.current_view == "dashboard":
        tab1, tab2, tab3 = st.tabs(["📊 仪表盘", "📅 项目甘特图", "🗂️ 数据管理"])
        
        # --- TAB 1: 看板 ---
        with tab1:
            if not df.empty:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("总任务", len(df))
                k2.metric("进行中", len(df[df["状态"]=="进行中"]))
                k3.metric("高优", len(df[df["重要性(1-10)"]>=8]))
                k4.metric("平均进度", f"{df['当前进度(%)'].mean():.0f}%")
                
                st.write("")
                with st.container(border=True):
                    st.subheader("🎯 四象限 (点击圆点进入详情)")
                    fig = px.scatter(df, x="紧急性(1-10)", y="重要性(1-10)", color="类别", text="任务名称", range_x=[0,11], range_y=[0,11], height=500)
                    fig.add_shape(type="rect", x0=5.5, y0=5.5, x1=11, y1=11, fillcolor="rgba(255,0,0,0.1)", layer="below", line_width=0)
                    fig.add_shape(type="rect", x0=0, y0=5.5, x1=5.5, y1=11, fillcolor="rgba(0,0,255,0.1)", layer="below", line_width=0)
                    fig.add_shape(type="rect", x0=5.5, y0=0, x1=11, y1=5.5, fillcolor="rgba(255,165,0,0.1)", layer="below", line_width=0)
                    fig.add_shape(type="rect", x0=0, y0=0, x1=5.5, y1=5.5, fillcolor="rgba(0,128,0,0.1)", layer="below", line_width=0)
                    fig.update_traces(textposition='top center', marker=dict(size=18, line=dict(width=1, color='gray')))
                    fig.update_layout(plot_bgcolor='white', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), margin=dict(l=20,r=20,t=20,b=20), font=dict(size=14))
                    
                    ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")
                    if ev.selection["points"]:
                        clicked_idx = ev.selection["points"][0]["point_index"]
                        st.session_state.selected_task_index = df.index[clicked_idx]
                        st.session_state.current_view = "detail"
                        st.rerun()
                
                st.write("")
                with st.container(border=True):
                    st.subheader("📈 进度趋势")
                    logs = get_logs()
                    if not logs.empty and not df.empty:
                        trend_proj = st.selectbox("选择项目查看趋势", df["任务名称"].unique())
                        proj_logs = logs[logs["项目"] == trend_proj].copy()
                        if not proj_logs.empty:
                            proj_logs["日期"] = pd.to_datetime(proj_logs["日期"])
                            proj_logs = proj_logs.sort_values("日期")
                            proj_logs["累计进度"] = proj_logs["贡献进度"].cumsum()
                            fig_burn = px.line(proj_logs, x="日期", y="累计进度", markers=True)
                            fig_burn.update_yaxes(range=[0, 105])
                            st.plotly_chart(fig_burn, use_container_width=True)
                        else:
                            st.caption("该项目暂无日志，去右侧添加一点吧！")
                    else:
                        st.caption("暂无日志数据")

                st.write("")
                st.subheader("📋 快速列表")
                edited_list = st.data_editor(
                    df[["任务名称", "类别", "截止日期", "状态", "当前进度(%)"]],
                    column_config={
                        "当前进度(%)": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=100),
                        "状态": st.column_config.SelectboxColumn(options=["未开始", "进行中", "已完成", "暂停"]),
                        "截止日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    },
                    use_container_width=True, hide_index=True
                )
                if not edited_list.equals(df[["任务名称", "类别", "截止日期", "状态", "当前进度(%)"]]):
                    df.update(edited_list)
                    save_data(df)
                    st.rerun()
            else:
                st.info("👈 左侧还没数据，或搜索无结果")

        # --- TAB 2: 甘特图 ---
        with tab2:
            if not df.empty:
                st.subheader("📆 时间轴视图")
                fig_g = px.timeline(df, x_start="开始时间", x_end="截止日期", y="任务名称", color="状态", height=400+len(df)*20,
                                    color_discrete_map={"已完成":"#28a745", "进行中":"#6f42c1", "未开始":"#999"})
                fig_g.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_g, use_container_width=True)
                
                st.subheader("📝 数据编辑器")
                edited_gantt = st.data_editor(
                    df,
                    column_config={
                        "开始时间": st.column_config.DateColumn(format="YYYY-MM-DD"),
                        "截止日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
                        "状态": st.column_config.SelectboxColumn(options=["未开始", "进行中", "已完成", "暂停"]),
                        "当前进度(%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
                        "项目编号": st.column_config.TextColumn(disabled=True)
                    },
                    num_rows="dynamic", use_container_width=True, height=500
                )
                if not edited_gantt.equals(df):
                    save_data(edited_gantt)
                    st.toast("✅ 已保存")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.info("暂无数据")

        # --- TAB 3: 数据管理 ---
        with tab3:
            st.subheader("🗑️ 项目管理")
            with st.container(border=True):
                st.write("**方式1：下拉删除**")
                to_delete = st.selectbox("选择任务", df["任务名称"].unique(), index=None, placeholder="请选择...")
                if to_delete:
                    if st.button(f"删除 {to_delete}", type="primary"):
                        df = df[df["任务名称"] != to_delete]
                        save_data(df)
                        st.success("删除成功！")
                        time.sleep(1)
                        st.rerun()
            st.write("**方式2：表格选中删除 (选中行号 -> Delete)**")
            edited_admin = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="admin_editor")
            if not edited_admin.equals(df):
                save_data(edited_admin)
                st.rerun()

    # === Detail ===
    elif st.session_state.current_view == "detail":
        idx = st.session_state.selected_task_index
        full_df = get_data()
        if idx is not None and idx in full_df.index:
            task = full_df.loc[idx]
            if st.button("⬅️ 返回看板"):
                st.session_state.current_view = "dashboard"
                st.rerun()
            
            with st.container(border=True):
                st.title(task["任务名称"])
                c1, c2, c3, c4 = st.columns(4)
                c1.info(f"ID: {task['项目编号']}")
                c2.warning(f"截止: {task['截止日期']}")
                c3.error(f"状态: {task['状态']}")
                c4.metric("进度", f"{task['当前进度(%)']}%")
                st.progress(int(task["当前进度(%)"])/100)
                st.divider()
                
                cm, cn = st.columns([1.5, 1])
                with cm:
                    st.subheader("✅ 子任务 (可直接删除)")
                    try: subs = json.loads(task["任务分解JSON"])
                    except: subs = []
                    
                    if subs: sub_df = pd.DataFrame(subs)
                    else: sub_df = pd.DataFrame(columns=["id", "name", "weight", "done"])

                    edited_subs = st.data_editor(
                        sub_df,
                        column_config={
                            "done": st.column_config.CheckboxColumn("完成", width="small"),
                            "name": st.column_config.TextColumn("子任务名", width="medium"),
                            "weight": st.column_config.NumberColumn("权重", width="small"),
                            "id": st.column_config.TextColumn("ID", disabled=True, width="small")
                        },
                        num_rows="dynamic", use_container_width=True, hide_index=True
                    )
                    
                    new_subs_json = edited_subs.to_dict(orient="records")
                    if json.dumps(new_subs_json) != task["任务分解JSON"]:
                        full_df.at[idx, "任务分解JSON"] = json.dumps(new_subs_json)
                        total_w = sum(int(x['weight']) for x in new_subs_json)
                        done_w = sum(int(x['weight']) for x in new_subs_json if x['done'])
                        new_prog = min(int((done_w/total_w)*100), 100) if total_w > 0 else 0
                        full_df.at[idx, "当前进度(%)"] = new_prog
                        save_data(full_df)
                        st.rerun()
                    
                    st.divider()
                    st.subheader("📜 本项目更新日志")
                    all_logs = get_logs()
                    if not all_logs.empty:
                        p_logs = all_logs[all_logs["项目"] == task["任务名称"]]
                        if not p_logs.empty:
                             st.dataframe(p_logs.sort_values("日期", ascending=False), use_container_width=True, hide_index=True)
                        else: st.caption("暂无记录")
                
                with cn:
                    st.subheader("📝 笔记")
                    n = st.text_area("内容", value=str(task["专属笔记"]), height=300)
                    if st.button("保存笔记"):
                        full_df.at[idx, "专属笔记"] = n
                        save_data(full_df)
                        st.success("已保存")
        else:
            st.session_state.current_view = "dashboard"
            st.rerun()

# ==========================================
# 右侧固定工具栏
# ==========================================
with col_right:
    # 1. 真实日历 (仅展示)
    with st.container(border=True):
        render_calendar()
    
    # 2. 每日更新 (日期选择器在这里)
    with st.container(border=True):
        st.subheader("📝 每日更新")
        # === 核心修改：日期选择器移入此处 ===
        log_date = st.date_input("1. 选择日期", value=datetime.now())
        
        full_df_right = get_data()
        
        if not full_df_right.empty:
            task_list = full_df_right["任务名称"].unique()
            selected_task_name = st.selectbox("2. 选择项目", task_list)
            
            selected_row = full_df_right[full_df_right["任务名称"] == selected_task_name].iloc[0]
            try: 
                sub_data = json.loads(selected_row["任务分解JSON"])
                sub_names = [s["name"] for s in sub_data]
            except: 
                sub_data = []
                sub_names = []
            
            if sub_names:
                selected_sub_name = st.selectbox("3. 选择子任务", sub_names)
                current_sub = next((s for s in sub_data if s["name"] == selected_sub_name), None)
                max_w = int(current_sub["weight"]) if current_sub else 100
                st.info(f"该子任务权重: **{max_w}%**")
                
                log_content = st.text_area("4. 今日内容", height=80)
                prog_incr = st.number_input("5. 贡献进度 (+%)", min_value=0, max_value=max_w, value=0)
                
                if st.button("提交更新", type="primary"):
                    save_log_entry(log_date.strftime("%Y-%m-%d"), selected_task_name, selected_sub_name, log_content, prog_incr)
                    
                    current_idx = full_df_right[full_df_right["任务名称"] == selected_task_name].index[0]
                    new_total = min(full_df_right.at[current_idx, "当前进度(%)"] + prog_incr, 100)
                    full_df_right.at[current_idx, "当前进度(%)"] = new_total
                    save_data(full_df_right)
                    st.success("已记录！")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("无子任务，请先添加")
        else:
            st.caption("暂无项目")

    # 3. 报表 & AI
    with st.container(border=True):
        st.subheader("📊 报表 & AI")
        t_rep, t_ai = st.tabs(["📄 周报", "🤖 拆解"])
        
        with t_rep:
            if st.button("生成本周周报"):
                logs = get_logs()
                if not logs.empty:
                    logs["日期"] = pd.to_datetime(logs["日期"])
                    start_date = pd.Timestamp.now() - pd.Timedelta(days=7)
                    weekly_logs = logs[logs["日期"] >= start_date]
                    if not weekly_logs.empty:
                        report_md = f"# 📅 本周工作汇报\n生成: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                        for proj, group in weekly_logs.groupby("项目"):
                            report_md += f"## 📌 {proj}\n"
                            for _, row in group.iterrows():
                                report_md += f"- **{row['日期'].strftime('%m-%d')}**: {row['内容']} (进度+{row['贡献进度']}%)\n"
                            report_md += "\n"
                        st.download_button("📥 下载 Markdown", report_md, "weekly_report.md")
                    else: st.warning("本周无记录")
                else: st.warning("无数据")

        with t_ai:
            st.caption("AI任务拆解演示")
            ai_input = st.text_input("任务目标", placeholder="例：准备答辩PPT")
            if st.button("✨ AI 拆解"):
                if ai_input:
                    st.code("1. 梳理逻辑 (20%)\n2. 制作初稿 (30%)\n3. 美化 (20%)\n4. 演练 (30%)")