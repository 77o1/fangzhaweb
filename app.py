import streamlit as st
import requests
import pandas as pd
import sqlite3
from datetime import datetime

# ==================== 🔑 请替换以下 3 个变量 ====================
API_KEY = "ark-c3aa8ccb-d6d8-416e-b33a-69e9807c45a2-94e0e" # 你的 API Key
API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"  # 你的 API 地址
MODEL_ID = "ep-20260720222605-bxxmz"   # ⚠️ 请到火山引擎控制台 → 模型推理 里查看，复制出来填这里
# =============================================================

# 风险分级定义
RISK_LEVEL = {
    "low": {"name": "低危｜可疑信息", "color": "#FFC107", "tip": "仅存在可疑话术，建议谨慎核实对方身份"},
    "mid": {"name": "中危｜存在诈骗嫌疑", "color": "#FF7F50", "tip": "请勿转账、不泄露验证码，联系辅导员确认"},
    "high": {"name": "高危｜立即停止操作！", "color": "#DC3545", "tip": "立刻终止聊天，切勿转账，保存证据报警！校保卫处：XXX-XXXXXXX 反诈专线：96110"}
}

# 八大校园诈骗知识库（基础数据）
fraud_knowledge = [
    {"type": "刷单返利", "keyword": "垫付、佣金、连单、提现失败", "desc": "先小额返利诱导大额充值，最后拉黑跑路"},
    {"type": "校园网贷", "keyword": "低息、无抵押、注销校园贷、征信修复", "desc": "以征信为由恐吓转账，收取保证金、解冻费"},
    {"type": "游戏账号交易", "keyword": "私下交易、第三方平台、押金、过户费", "desc": "虚假平台冻结资金，要求持续充值解冻"},
    {"type": "冒充客服", "keyword": "订单异常、理赔、退款、快递丢失", "desc": "发送虚假链接套取银行卡、验证码"},
    {"type": "冒充导师/领导", "keyword": "急事、转账、保密、不要告诉别人", "desc": "AI换脸/语音克隆伪装师长借钱转账"},
    {"type": "虚假兼职", "keyword": "日入几百、居家轻松、培训缴费", "desc": "收取报名费、工装费后失联"},
    {"type": "中奖返利", "keyword": "免费领奖、税费、保证金、先转账", "desc": "以中奖为由索要手续费、公证费"},
    {"type": "AI深度伪造诈骗", "keyword": "视频通话、语音借钱、人脸核验", "desc": "AI换脸、克隆语音冒充亲友实施诈骗"}
]

# ---------- 数据库初始化 ----------
def init_db():
    conn = sqlite3.connect("fraud_db.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS fraud_lib
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fraud_type TEXT,
                  keywords TEXT,
                  content TEXT,
                  update_time TEXT)''')
    for item in fraud_knowledge:
        c.execute("INSERT OR IGNORE INTO fraud_lib (fraud_type, keywords, content, update_time) VALUES (?,?,?,?)",
                  (item["type"], item["keyword"], item["desc"], str(datetime.now())))
    conn.commit()
    conn.close()

# ---------- 本地知识库检索 ----------
def search_knowledge(user_text):
    conn = sqlite3.connect("fraud_db.db")
    df = pd.read_sql("SELECT * FROM fraud_lib", conn)
    conn.close()
    hit_list = []
    for _, row in df.iterrows():
        kw_list = row["keywords"].split("、")
        for kw in kw_list:
            if kw in user_text:
                hit_list.append(row)
                break
    return hit_list

# ---------- 调用大模型 API ----------
def get_fraud_answer(user_input, hit_knowledge):
    hit_text = "\n".join([f"{x['fraud_type']}：{x['content']}" for x in hit_knowledge]) if hit_knowledge else "无匹配典型骗局关键词"
    
    prompt = f'''
你是【校园防诈智盾】大学生反诈AI助手，只处理校园诈骗风险判断，严格遵守以下规则：
1. 优先使用下方官方校园反诈知识库内容作答，不输出无关内容；
2. 先判定风险等级：低危/中危/高危，必须明确标注；
3. 拆解骗局类型、风险关键词、防范措施、止损操作；
4. 结尾附上报警渠道：96110反诈专线、本校保卫处；
5. 语言通俗易懂，适配大学生，禁止专业晦涩话术；
6. 如果识别到AI换脸、冒充导师、刷单、校园贷，直接判定高危。

【校园反诈知识库匹配内容】
{hit_text}

【学生可疑提问内容】
{user_input}

输出格式：
风险等级：xxx
骗局类型：xxx
风险拆解：xxx
防范建议：xxx
紧急处置：xxx
'''
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ API调用失败（{str(e)}）\n\n本地知识库匹配结果：\n{hit_text}\n请检查网络或API配置，稍后重试。"

# ---------- 页面 UI ----------
def main():
    init_db()
    st.set_page_config(page_title="校园防诈智盾", page_icon="🛡️", layout="wide")
    st.title("🛡️ 校园防诈智盾 —— 大学生诈骗风险智能问答助手")
    st.subheader("7×24小时反诈风险核验工具｜零隐私采集，安全合规")
    st.divider()

    # 侧边栏
    with st.sidebar:
        st.header("功能导航")
        menu = st.radio("请选择功能", ["智能风险问答", "反诈知识库查询", "风险分级说明"])
        st.divider()
        st.warning("本系统不会存储你的手机号、身份证等隐私，对话可一键清空")
        if st.button("清空本次对话缓存"):
            if "chat_history" in st.session_state:
                st.session_state["chat_history"] = []
            st.success("对话缓存已清空")

    # 初始化对话历史
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # 模块1：智能风险问答
    if menu == "智能风险问答":
        st.markdown("### 🔍 粘贴可疑聊天/兼职/转账信息，AI实时识别诈骗风险")
        user_msg = st.text_area("输入需要核验的内容：", height=150, placeholder="例：导师让我私下转一笔钱，不要告诉辅导员；网上刷单垫付返佣金...")
        submit_btn = st.button("一键核验风险", type="primary")

        if submit_btn and user_msg.strip() != "":
            with st.spinner("AI正在匹配反诈知识库，识别风险点..."):
                hit_result = search_knowledge(user_msg)
                ai_reply = get_fraud_answer(user_msg, hit_result)
                st.session_state["chat_history"].append({"user": user_msg, "ai": ai_reply})

        # 显示历史对话
        for item in reversed(st.session_state["chat_history"]):
            st.markdown(f"**学生提问：**\n{item['user']}")
            st.markdown(f"**AI反诈判定结果：**\n{item['ai']}")
            st.divider()

    # 模块2：反诈知识库查询
    elif menu == "反诈知识库查询":
        st.markdown("### 📚 八大校园高发骗局案例库")
        df_lib = pd.DataFrame(fraud_knowledge)
        st.dataframe(df_lib, use_container_width=True)
        search_type = st.selectbox("按骗局类型检索", ["全部"] + [i["type"] for i in fraud_knowledge])
        if search_type != "全部":
            filter_data = df_lib[df_lib["type"] == search_type]
            st.table(filter_data)

    # 模块3：风险分级说明
    elif menu == "风险分级说明":
        st.markdown("### ⚠️ 三级风险处置标准")
        for k, v in RISK_LEVEL.items():
            st.markdown(f"""
            <div style="background:{v['color']};padding:10px;border-radius:8px;color:#000;margin-bottom:10px;">
                <h4>{v['name']}</h4>
                <p>{v['tip']}</p >
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.caption("项目：校园防诈智盾｜无隐私采集｜平安校园数字化工具")

if __name__ == "__main__":
    main()
