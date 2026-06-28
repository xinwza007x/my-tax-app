import streamlit as st
import requests
import json

# 1. ตั้งค่าหน้าเว็บธีมมืดและกว้าง (Wide Mode)
st.set_page_config(page_title="Slash Tax Planner", layout="wide", initial_sidebar_state="collapsed")

# ปรับแต่งสไตล์ CSS ให้สีพื้นหลังและ UI มืดสนิทแบบพรีเมียมตามรูปของคุณ
st.markdown("""
<style>
    .stApp { background-color: #030712; color: #f3f4f6; }
    div[data-testid="stMetricValue"] { color: #f3f4f6 !important; font-weight: 800 !important; }
    .stButton>button { background-color: #10b981 !important; color: #030712 !important; font-weight: bold !important; width: 100%; border-radius: 8px; }
    .stProgress > div > div > div > div { background-color: #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)

# ----------------- อัตราภาษีเงินได้บุคคลธรรมดาของไทย -----------------
TAX_BRACKETS = [
    {"min": 0, "max": 150000, "rate": 0.00, "text": "0 - 150,000 บาท"},
    {"min": 150001, "max": 300000, "rate": 0.05, "text": "150,001 - 300,000 บาท"},
    {"min": 300001, "max": 500000, "rate": 0.10, "text": "300,001 - 500,000 บาท"},
    {"min": 500001, "max": 750000, "rate": 0.15, "text": "500,001 - 750,000 บาท"},
    {"min": 750001, "max": 1000000, "rate": 0.20, "text": "750,001 - 1,000,000 บาท"},
    {"min": 1000001, "max": 2000000, "rate": 0.25, "text": "1,000,001 - 2,000,000 บาท"},
    {"min": 2000001, "max": 5000000, "rate": 0.30, "text": "2,000,001 - 5,000,000 บาท"},
    {"min": 5000001, "max": float('inf'), "rate": 0.35, "text": "มากกว่า 5,000,000 บาท"}
]

# ข้อมูลรายละเอียดของแต่ละมาตราสำหรับแสดงผลและคำนวณ
INCOME_RULES = {
    "มาตรา 40(1) : เงินเดือน / ค่าจ้าง": {"rate": 0.50, "max": 100000, "is_combined": True, "desc": "เงินได้จากการจ้างแรงงาน เช่น เงินเดือน โบนัส ค่าคอมมิชชันพนักงานประจำ"},
    "มาตรา 40(2) : รับจ้างอิสระ / ฟรีแลนซ์ / คอมมิชชัน / Affiliate": {"rate": 0.50, "max": 100000, "is_combined": True, "desc": "เงินได้จากหน้าที่หรือตำแหน่งงานที่ทำ เช่น ค่าจ้างฟรีแลนซ์ทั่วไป นายหน้า ค่าแนะนำ TikTok/Shopee Affiliate ขับแกร็บส่งของ"},
    "มาตรา 40(3) : ค่าลิขสิทธิ์ / ทรัพย์สินทางปัญญา / เขียนบทความ": {"rate": 0.50, "max": 100000, "is_combined": False, "desc": "ค่ากู๊ดวิลล์ ลิขสิทธิ์ หรือสิทธิอย่างอื่น เช่น ค่าแต่งหนังสือ ลิขสิทธิ์เพลง สิทธิบัตร"},
    "มาตรา 40(4) : ดอกเบี้ย / เงินปันผล / คริปโทเคอร์เรนซี": {"rate": 0.00, "max": 0, "is_combined": False, "desc": "เงินได้จากการลงทุน เช่น ดอกเบี้ยเงินฝาก เงินปันผลจากหุ้น กำไรจากการขายสินทรัพย์ดิจิทัล *ตามกฎหมายหักค่าใช้จ่ายไม่ได้"},
    "มาตรา 40(5) : ค่าเช่าทรัพย์สิน": {"rate": 0.30, "max": float('inf'), "is_combined": False, "desc": "เงินได้จากการให้เช่าทรัพย์สิน เช่น เช่าบ้าน คอนโดมิเนียม รถยนต์ ที่ดิน"},
    "มาตรา 40(6) : วิชาชีพอิสระ (แพทย์/กฎหมาย/วิศวกร/บัญชี)": {"rate": 0.30, "max": float('inf'), "is_combined": False, "desc": "วิชาชีพอิสระที่กฎหมายกำหนดไว้ 6 สาขาวิชาชีพ (โรคศิลป์/แพทย์ หักเหมาได้ 60% ส่วนวิชาชีพอื่นหักเหมา 30%)"},
    "มาตรา 40(7) : รับเหมาค่าแรงและวัสดุ": {"rate": 0.60, "max": float('inf'), "is_combined": False, "desc": "งานรับเหมาที่ผู้รับเหมาต้องจัดหาพัสดุในส่วนสำคัญนอกเหนือจากเครื่องมือ เช่น รับเหมาก่อสร้างที่มีวัสดุ"},
    "มาตรา 40(8) : การพาณิชย์ / ขายของออนไลน์ / ยูทูบเบอร์ / ธุรกิจอื่นๆ": {"rate": 0.60, "max": float('inf'), "is_combined": False, "desc": "เงินจากการธุรกิจ การพาณิชย์ การเกษตร หรือขายของออนไลน์ทั่วไป ที่ไม่เข้าพวกมาตรา 40(1)-(7)"}
}

# ----------------- ส่วนหัวเว็บบอร์ด (Navbar) -----------------
nav1, nav2 = st.columns([8, 4])
with nav1:
    st.markdown("## ✨ Slash Tax Planner")
    st.caption("ระบบ AI อัตโนมัติ วางแผนภาษีสำหรับคนทำงานหลายบทบาท")
with nav2:
    st.markdown("<div style='text-align:right; color:#10b981; font-weight:bold; font-size:13px;'>🟢 AI Agent Online (High Stability)</div>", unsafe_allow_html=True)
    
    # 💡 ตรรกะดักจับคีย์: 
    # ถ้าผู้ใช้พิมพ์ใส่ช่อง (ถ้ามี) ให้ใช้คีย์เขา แต่ถ้าไม่มี ให้แอบดึงคีย์ฟรีที่เราเซตไว้หลังบ้านมาทำงานออโต้
    try:
        FINAL_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    except:
        # หากรันในเครื่องตัวเอง (Local) แล้วยังไม่ได้สร้างไฟล์ความลับ ให้ใส่รหัสคีย์ฟรีของคุณตรงนี้ได้เลย!
        FINAL_API_KEY = ""

# ----------------- จัดสัดส่วนหน้าจอซ้าย-ขวา (5:7) -----------------
col1, col2 = st.columns([5, 7])

# ใช้ Session State เพื่อจำลองคลังพอร์ตรายได้ของผู้ใช้ให้สามารถกดเพิ่ม/ลบได้จริง
if "my_income_portfolio" not in st.session_state:
    st.session_state.my_income_portfolio = [
        {"name": "งานประจำ (เงินเดือน)", "amount": 360000, "category": "มาตรา 40(1) : เงินเดือน / ค่าจ้าง", "freq": 12},
    ]

with col1:
    st.markdown("### 🟢 Agent 1: Slash Mapper")
    st.caption("ระบบจำแนกรายได้พึงประเมินและประเมินค่าใช้จ่าย")
    
    st.markdown("**พอร์ตโฟลิโอรายได้ของคุณในปัจจุบัน:**")
    
    # ตัวแปรคำนวณฐานข้อมูลรวมสำหรับใช้ประมวลผลฝั่งขวา
    total_gross = 0
    vat_applicable_income = 0
    bank_count = 0
    m40_1_2_combined_gross = 0
    expenses_breakdown = {k: 0.0 for k in INCOME_RULES.keys()}

    # --- ส่วนที่แก้ไข: ลูปแสดงรายชื่อพร้อมทำปุ่มลบออกซ้าย-ขวา ---
    if len(st.session_state.my_income_portfolio) == 0:
        st.warning("⚠️ ตอนนี้พอร์ตว่างเปล่า กรุณาเพิ่มแหล่งรายได้ด้านล่างครับ")
    else:
        for idx, stream in enumerate(st.session_state.my_income_portfolio):
            total_gross += stream["amount"]
            bank_count += stream["freq"]
            if "มาตรา 40(1)" not in stream["category"]:
                vat_applicable_income += stream["amount"]
                
            if INCOME_RULES[stream["category"]]["is_combined"]:
                m40_1_2_combined_gross += stream["amount"]
            else:
                rule = INCOME_RULES[stream["category"]]
                expenses_breakdown[stream["category"]] += min(stream["amount"] * rule["rate"], rule["max"])

            # แบ่งสัดส่วนข้อมูล 10 ส่วน : ปุ่มลบ 2 ส่วน (เพื่อให้อยู่ระนาบเดียวกันแบบสมดุล)
            card_text_col, card_btn_col = st.columns([10, 2])
            
            with card_text_col:
                st.info(f"💼 **{stream['name']}** | {stream['category'].split(' : ')[0]} | {stream['amount']:,} บาท/ปี (รับเงิน {stream['freq']} ครั้ง/ปี)")
            
            with card_btn_col:
                # ทำปุ่มลบแยกตามค่าดัชนี (Index) ของอาร์เรย์พอร์ตโฟลิโอ
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.my_income_portfolio.pop(idx)
                    st.rerun() # รีเซตหน้าจอทันทีเพื่อตัดรายชื่อออก

    st.markdown("---")
    st.markdown("#### ➕ เพิ่มแหล่งเงินได้ของชาว Slash")
    new_job = st.text_input("ชื่องานพาร์ตไทม์/งานประจำ", placeholder="เช่น รับวาดสติกเกอร์ไลน์, ปล่อยเช่าคอนโด, ดอกเบี้ย")
    
    in_col1, in_col2 = st.columns(2)
    with in_col1:
        new_amt = st.number_input("รายรับรวม (บาท/ปี)", min_value=0, value=0, step=5000)
    with in_col2:
        new_freq = st.number_input("ความถี่รับเงิน (ครั้ง/ปี)", min_value=0, value=12)
        
    selected_cat = st.selectbox("ประเภทภาษี (เลือกให้ตรงกับงานของคุณเพื่อการคำนวณที่ถูกต้อง)", list(INCOME_RULES.keys()), index=1)
    
    st.markdown(f"""
    <div style='background-color:#0f172a; padding:12px; border-radius:8px; border:1px solid #1e293b; font-size:11px; color:#94a3b8;'>
        <strong>{selected_cat.split(' : ')[0]} คืออะไร?</strong><br>
        {INCOME_RULES[selected_cat]['desc']}<br>
        <span style='color:#10b981; font-weight:bold;'>กฎการหักต้นทุน: {
            "หักค่าใช้จ่ายเหมาได้ 50% แต่เมื่อรวมกับมาตรา 40(1) และ 40(2) แล้วต้องไม่เกิน 100,000 บาท" if INCOME_RULES[selected_cat]['is_combined'] 
            else f"หักค่าใช้จ่ายแบบเหมาได้ {INCOME_RULES[selected_cat]['rate']*100:.0f}%" if INCOME_RULES[selected_cat]['rate'] > 0 
            else "ไม่สามารถหักค่าใช้จ่ายได้ตามกฎหมาย"
        }</span>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ บันทึกเข้าพอร์ตโฟลิโอรายได้"):
        if new_job and new_amt > 0:
            st.session_state.my_income_portfolio.append({
                "name": new_job, "amount": new_amt, "category": selected_cat, "freq": new_freq
            })
            st.rerun() # สั่งรีรันเพื่อแสดงรายการใหม่ขึ้นบล็อกด้านบนทันที

    if st.button("🔄 รีเซ็ตข้อมูลกลับเป็นค่าเริ่มต้น"):
        st.session_state.my_income_portfolio = [
            {"name": "งานประจำ (เงินเดือน)", "amount": 360000, "category": "มาตรา 40(1) : เงินเดือน / ค่าจ้าง", "freq": 12},
            {"name": "ฟรีแลนซ์ ออกแบบกราฟิก", "amount": 180000, "category": "มาตรา 40(2) : รับจ้างอิสระ / ฟรีแลนซ์ / คอมมิชชัน / Affiliate", "freq": 24},
            {"name": "นายหน้า Shopee Affiliate", "amount": 90000, "category": "มาตรา 40(2) : รับจ้างอิสระ / ฟรีแลนซ์ / คอมมิชชัน / Affiliate", "freq": 85}
        ]
        st.rerun()

    # ส่วนลดหย่อนมาตรฐานพื้นฐานคงเดิม
    social_security = 9000
    personal_deduct = 60000
    total_deductions = personal_deduct + social_security

# ----------------- ตรรกะคำนวณภาษีฝั่งขวา -----------------
# คำนวณกลุ่ม 40(1) และ 40(2) รวมกันไม่เกิน 100,000
allowed_combined_expense = min(m40_1_2_combined_gross * 0.5, 100000)

# รวมยอดค่าใช้จ่ายทั้งหมดพึงหักได้จริง
total_allowed_expenses = allowed_combined_expense + sum(expenses_breakdown.values())

# เงินได้สุทธิ = รายได้รวม - ค่าใช้จ่ายรวม - ค่าลดหย่อนรวม
net_taxable_income = max(0, (total_gross - total_allowed_expenses - total_deductions))

# คิดคำนวณเงินภาษีแต่ละขั้นบันไดสะสมแบบละเอียด
remaining_income = net_taxable_income
total_tax_payable = 0
bracket_table_rows = ""
current_bracket_rate = "0%"

for bracket in TAX_BRACKETS:
    bracket_range = bracket["max"] - bracket["min"] + 1
    income_in_this_bracket = 0
    if remaining_income > 0:
        current_bracket_rate = f"{bracket['rate']*100:.0f}%"
        if remaining_income > bracket_range:
            income_in_this_bracket = bracket_range
            remaining_income -= bracket_range
        else:
            income_in_this_bracket = remaining_income
            remaining_income = 0
    tax_in_bracket = income_in_this_bracket * bracket["rate"]
    total_tax_payable += tax_in_bracket
    
    # ไฮไลท์แถวที่มีการเสียภาษีจริงด้วยสีเขียวเข้มแบบแดชบอร์ดต้นฉบับ
    row_bg = "background-color:#022c22; color:#6ee7b7;" if tax_in_bracket > 0 or (income_in_this_bracket > 0 and bracket['rate'] == 0) else ""
    bracket_table_rows += f"<tr style='{row_bg}'><td style='padding:8px;'>{bracket['text']}</td><td style='padding:8px; text-align:center;'>{bracket['rate']*100:.0f}%</td><td style='padding:8px; text-align:right;'>{income_in_this_bracket:,.0f} บาท</td><td style='padding:8px; text-align:right;'>{tax_in_bracket:,.1f} บาท</td></tr>"

# ----------------- ส่วนฝั่งขวา: DASHBOARD DISPLAY -----------------
with col2:
    st.markdown("### 📄 ส่วนที่ 1: สรุปยอดวิเคราะห์และคำนวณตัวเลขภาษี")
    st.caption("วิเคราะห์โครงสร้างต้นทุนและเงินได้สุทธิของระบบ Agent 2")
    
    # กล่อง KPI 3 บล็อกใหญ่ตามรูปภาพของคุณ
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:12px; border:1px solid #1e293b;'>รายได้รวมพึงประเมิน<br><span style='font-size:22px; font-weight:bold;'>{total_gross:,.0f}</span> ยอดบาท<br><span style='font-size:10px; color:#64748b;'>รายได้สะสมของทุกมาตรา 40</span></div>", unsafe_allow_html=True)
    with kpi_col2:
        st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:12px; border:1px solid #1e293b;'>เงินได้สุทธิสำหรับคิดภาษี<br><span style='font-size:22px; font-weight:bold; color:#2dd4bf;'>{net_taxable_income:,.0f}</span> ยอดบาท<br><span style='font-size:10px; color:#64748b;'>หลังหักต้นทุนและลดหย่อนแล้ว</span></div>", unsafe_allow_html=True)
    with kpi_col3:
        st.markdown(f"<div style='background-color:#064e3b; padding:15px; border-radius:12px; border:1px solid #065f46;'>ประมาณการภาษีที่ต้องจ่าย<br><span style='font-size:24px; font-weight:900; color:#34d399;'>{total_tax_payable:,.1f}</span> ยอดบาท<br><span style='font-size:10px; color:#94a3b8;'>ฐานภาษีสูงสุดของคุณ: {current_bracket_rate}</span></div>", unsafe_allow_html=True)

    # กราฟแท่งแสดงกระแสและการไหลของเงินได้พึงประเมิน (Progress Bars)
    st.markdown("#### กระแสสัญญะและการไหลของเงินได้พึงประเมิน (THB)")
    
    st.markdown(f"<div style='font-size:11px; display:flex; justify-content:space-between;'><span>1. รายรับทั้งหมด (100%)</span><span>{total_gross:,.0f} บาท</span></div>", unsafe_allow_html=True)
    st.progress(1.0)
    
    exp_pct = (total_allowed_expenses / total_gross * 100) if total_gross > 0 else 0
    st.markdown(f"<div style='font-size:11px; display:flex; justify-content:space-between;'><span>2. หักค่าใช้จ่ายตามมาตรา 40 (เหมา/จริง)</span><span style='color:#f59e0b;'>-{total_allowed_expenses:,.0f} บาท ({exp_pct:.0f}%)</span></div>", unsafe_allow_html=True)
    st.progress(min(1.0, total_allowed_expenses / total_gross) if total_gross > 0 else 0)
    
    st.markdown(f"<div style='font-size:11px; display:flex; justify-content:space-between;'><span>3. หักค่าลดหย่อนภาษีเพิ่มเติม</span><span style='color:#f43f5e;'>-{total_deductions:,.0f} บาท</span></div>", unsafe_allow_html=True)
    st.progress(min(1.0, total_deductions / total_gross) if total_gross > 0 else 0)
    
    st.markdown(f"<div style='font-size:12px; font-weight:bold; color:#10b981; margin-top:5px; text-align:right;'>4. ยอดเงินได้สุทธิที่นำมาคำนวณภาษีจริง: {net_taxable_income:,.0f} บาท</div>", unsafe_allow_html=True)

    # ตารางแจกแจงสัดส่วนขั้นบันไดภาษีเรนเดอร์ HTML
    st.markdown("#### ตารางแสดงสัดส่วนขั้นบันไดภาษีที่คำนวณได้")
    st.markdown(f"<table style='width:100%; border-collapse: collapse; font-size:11px; text-align:left; background-color:#0f172a; border:1px solid #1e293b;'>"
                f"<tr style='background-color:#1e293b; color:#94a3b8; font-weight:bold;'><th style='padding:8px;'>ช่วงเงินได้สุทธิ</th><th style='padding:8px; text-align:center;'>อัตราภาษี</th><th style='padding:8px; text-align:right;'>เงินได้ในขั้นนี้</th><th style='padding:8px; text-align:right;'>ภาษีที่คิดได้</th></tr>"
                f"{bracket_table_rows}"
                f"</table>", unsafe_allow_html=True)

    # ----------------- ส่วนที่ 2: ระบบประเมินความเสี่ยงภาษีย้อนหลัง (ออโต้รันตามเวลาจริง) -----------------
    st.markdown("---")
    st.markdown("### ⚠️ ส่วนที่ 2: ระบบประเมินความเสี่ยงภาษีย้อนหลัง (Audit Guardrails)")
    
    is_vat_heavy = vat_applicable_income > 1800000
    is_bank_heavy = bank_count >= 3000 or (bank_count >= 400 and total_gross >= 2000000)
    
    if is_vat_heavy or is_bank_heavy:
        st.markdown("<div style='padding:12px; background-color:#451a03; border:1px solid #78350f; color:#f59e0b; border-radius:8px; font-size:12px; font-weight:bold; margin-bottom:10px;'>🔴 ผลการประเมิน: มีความเสี่ยงสูงที่จะโดนเรียกเก็บย้อนหลัง</div>", unsafe_allow_html=True)
        if is_vat_heavy: st.warning(f"รายได้จากฝั่งธุรกิจ/รับจ้างภายนอกของคุณรวมสะสมอยู่ที่ {vat_applicable_income:,.0f} บาท ซึ่งเกินเกณฑ์เพดาน 1.8 ล้านบาท/ปี ต้องยื่นจดทะเบียนภาษีมูลค่าเพิ่ม (VAT)")
        if is_bank_heavy: st.warning(f"ยอดธุรกรรมการเงินขาเข้าในพอร์ตมีจำนวนสะสมถึง {bank_count} ครั้ง เข้าข่ายเงณฑ์รายงานอัตโนมัติของกฎหมาย e-Payment")
    else:
        st.markdown("<div style='padding:12px; background-color:#022c22; border:1px solid #065f46; color:#34d399; border-radius:8px; font-size:12px; font-weight:bold;'>🟢 ผลการประเมิน: ระดับความเสี่ยงต่ำ บัญชียังปลอดภัยดี</div>", unsafe_allow_html=True)
        st.caption("พฤติกรรมการเดินบัญชีและเกณฑ์ยอดเงินได้สะสมของพอร์ตปัจจุบันของคุณยังไม่กระตุ้นระบบสแกนของกรมสรรพากร")

    # ----------------- ส่วนที่ 3: แชตบอตถามตอบ AI -----------------
    st.markdown("---")
    st.markdown("### 💬 ส่วนที่ 3: ปรึกษาวางแผนภาษีกับ AI Final Advisor")
    
    user_query = st.text_input("พิมพ์คำถามของคุณที่นี่เพื่อปรึกษากลยุทธ์กับ AI:", placeholder="เช่น มีรายได้มาตรา 40(5) ปล่อยเช่าคอนโด ควรหักค่าใช้จ่ายตามจริงหรือเหมาคุ้มกว่ากัน...")
    
    if st.button("ส่งคำถามหา AI Expert"):
        if user_query:
            if not FINAL_API_KEY:
                st.error("❌ ระบบยังไม่ได้ตั้งค่ากุญแจเชื่อมต่อ โปรดนำ API Key ไปใส่ในเมนู Settings > Secrets บน Streamlit Cloud ก่อนครับ")
            else:
                # ประกอบ Prompt ข้อมูลตัวเลขส่งให้ AI
                ai_prompt = f"""คุณคือ "พี่ถุงเงิน Slash Tax Pro" ที่ปรึกษาวางแผนภาษีบุคคลธรรมดาชั้นนำของไทย ตอบคำถามด้วยน้ำเสียงที่เป็นมิตร ย่อยเรื่องยากให้เข้าใจง่าย
                นี่คือพอร์ตรายได้รวมของผู้ใช้ในปัจจุบัน: ยอดรวม {total_gross} บาท, มีเงินได้สุทธิหลังหักลดหย่อนแล้ว {net_taxable_income} บาท, ต้องชำระภาษี {total_tax_payable} บาท
                สถานะความเสี่ยงย้อนหลัง: {'ความเสี่ยงสูง' if (is_vat_heavy or is_bank_heavy) else 'ปลอดภัยความเสี่ยงต่ำ'}
                
                คำถามของผู้ใช้: "{user_query}"
                จงสรุปแนวทางอุดรอยรั่วภาษี แนะนำไอเดียกองทุนหรือสิทธิ์ลดหย่อนเพิ่มเติมที่ถูกกฎหมายและเหมาะสมกับพอร์ตของเขามาเป็นข้อๆ"""
                
                with st.spinner("The Final Advisor กำลังประมวลข้อมูลกฎหมายและสัดส่วนตัวเลขของคุณ..."):
                    headers = {'Content-Type': 'application/json'}
                    payload = {
                        "contents": [
                            {
                                "parts": [{"text": ai_prompt}]
                            }
                        ]
                    }
                    
                    # 💡 ลิสต์รายการ URL เส้นทางเชื่อมต่อ (Endpoints) ที่เราจะสุ่มยิงเพื่อหาเส้นทางที่ตอบกลับได้จริง
                    # สลับเปลี่ยนสัดส่วนเวอร์ชัน v1beta และชื่อรุ่นโมเดลเพื่อป้องกันปัญหา 404 ของ Google
                    api_endpoints = [
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={FINAL_API_KEY}",
                        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={FINAL_API_KEY}",
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={FINAL_API_KEY}"
                    ]
                    
                    success_reply = False
                    
                    for url in api_endpoints:
                        try:
                            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
                            res_json = response.json()
                            
                            if response.status_code == 200:
                                ai_reply = res_json['candidates'][0]['content']['parts'][0]['text']
                                st.success(ai_reply)
                                success_reply = True
                                break # ลูปเจอเส้นทางที่ถูกต้องแล้ว ให้หยุดการทำงานทันที
                        except Exception as e:
                            continue # หากเส้นทางนี้พัง ให้ข้ามไปสุ่มยิงเส้นทางถัดไปในรายการ
                            
                    if not success_reply:
                        st.error("❌ Google API Error: ไม่สามารถเชื่อมต่อช่องสัญญาณโมเดล AI ของกูเกิลได้ในขณะนี้ โปรดตรวจสอบความถูกต้องของรหัส API Key หรือลองกดใหม่อีกครั้งในภายหลังครับ")
