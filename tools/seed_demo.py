#!/usr/bin/env python3
"""
Demo seed script — Olorien Secondary School.
Matches the actual PostgreSQL schema on the server.
Safe to re-run (ON CONFLICT DO NOTHING everywhere).
"""
import os, sys, random, datetime, bcrypt
import psycopg2, psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql://school_mis:CHANGE_ME_strong_random_password@localhost:5432/school_mis")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def x(sql, p=()):   cur.execute(sql, p)
def one(sql, p=()): cur.execute(sql, p); r = cur.fetchone(); return dict(r) if r else None
def all_(sql, p=()): cur.execute(sql, p); return [dict(r) for r in cur.fetchall()]
def hpw(pw):        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(10)).decode()

TODAY = datetime.date.today()
YEAR  = TODAY.year

# ── Existing anchors ──────────────────────────────────────────────────────────
ay = one("SELECT id FROM academic_years WHERE is_current=1 LIMIT 1")
AY = ay["id"] if ay else 1

print("=== Seeding Olorien Secondary School ===\n")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Terms
# ─────────────────────────────────────────────────────────────────────────────
print("[1/12] Terms…")
for i, (name, s, e) in enumerate([
    ("Term 1", f"{YEAR}-01-15", f"{YEAR}-04-05"),
    ("Term 2", f"{YEAR}-04-22", f"{YEAR}-07-19"),
    ("Term 3", f"{YEAR}-08-05", f"{YEAR}-11-08"),
]):
    x("""INSERT INTO terms (academic_year_id, name, start_date, end_date, is_current, is_locked)
         VALUES (%s,%s,%s,%s,%s,0) ON CONFLICT DO NOTHING""",
      (AY, name, s, e, 1 if i == 0 else 0))

term_ids = [r["id"] for r in all_(
    "SELECT id FROM terms WHERE academic_year_id=%s ORDER BY id", (AY,))]

# ─────────────────────────────────────────────────────────────────────────────
# 2. Classes  (grade_level = form number)
# ─────────────────────────────────────────────────────────────────────────────
print("[2/12] Classes…")
CLASS_DEFS = [
    ("Form I A",1),("Form I B",1),
    ("Form II A",2),("Form II B",2),
    ("Form III A",3),("Form III B",3),
    ("Form IV A",4),("Form IV B",4),
    ("Form V A",5),("Form V B",5),
    ("Form VI A",6),("Form VI B",6),
]
for name, lvl in CLASS_DEFS:
    x("""INSERT INTO classes (name, grade_level, academic_year_id, capacity)
         VALUES (%s,%s,%s,45) ON CONFLICT DO NOTHING""", (name, lvl, AY))

CLS = {r["name"]: r["id"] for r in all_("SELECT id, name FROM classes WHERE academic_year_id=%s", (AY,))}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Subjects
# ─────────────────────────────────────────────────────────────────────────────
print("[3/12] Subjects…")
SUBJ_DEFS = [
    ("Mathematics","MATH"),("English Language","ENG"),("Kiswahili","KIS"),
    ("Biology","BIO"),("Chemistry","CHEM"),("Physics","PHY"),
    ("History","HIST"),("Geography","GEO"),("Civics","CIV"),
    ("Computer Science","CS"),("Commerce","COM"),("Accountancy","ACC"),
    ("Agriculture","AGRI"),("Physical Education","PE"),
    ("Islamic Studies","ISL"),("Bible Knowledge","BK"),
]
for name, code in SUBJ_DEFS:
    x("INSERT INTO subjects (name, code) VALUES (%s,%s) ON CONFLICT DO NOTHING", (name, code))

SUBJ = {r["code"]: r["id"] for r in all_("SELECT id, code FROM subjects")}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Teachers + user accounts
# ─────────────────────────────────────────────────────────────────────────────
print("[4/12] Teachers…")
TEACHERS = [
    ("Amina","Mwangi","Female","+255711001001","BSc Education","class_teacher"),
    ("Joseph","Kimani","Male","+255711001002","BSc Mathematics","class_teacher"),
    ("Fatuma","Hassan","Female","+255711001003","BA Kiswahili","class_teacher"),
    ("David","Ochieng","Male","+255711001004","BSc Physics","class_teacher"),
    ("Grace","Ndungu","Female","+255711001005","BSc Chemistry","class_teacher"),
    ("Ibrahim","Salim","Male","+255711001006","BA History","class_teacher"),
    ("Rose","Wanjiku","Female","+255711001007","BA Geography","subject_teacher"),
    ("Peter","Mutua","Male","+255711001008","BA English","subject_teacher"),
    ("Zainab","Ally","Female","+255711001009","BSc IT","subject_teacher"),
    ("Hassan","Juma","Male","+255711001010","BCom","subject_teacher"),
    ("Mary","Chege","Female","+255711001011","BCom Accounting","subject_teacher"),
    ("Ahmed","Omar","Male","+255711001012","BSc Agriculture","subject_teacher"),
    ("Agnes","Kariuki","Female","+255711001013","BEd PE","subject_teacher"),
    ("Samuel","Kamau","Male","+255711001014","BA Political Science","subject_teacher"),
    ("Leila","Rashid","Female","+255711001015","BA Islamic Studies","subject_teacher"),
]
pw_hash = hpw("Teacher@2025")
teacher_ids = []
for fn, ln, gen, ph, qual, role in TEACHERS:
    x("""INSERT INTO teachers (first_name, last_name, gender, phone, qualification,
              hire_date, is_active)
         VALUES (%s,%s,%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
      (fn, ln, gen, ph, qual, f"{YEAR}-01-10"))
    t = one("SELECT id FROM teachers WHERE first_name=%s AND last_name=%s", (fn, ln))
    if not t: continue
    tid = t["id"]; teacher_ids.append(tid)
    uname = f"{fn.lower()}.{ln.lower()}"
    x("""INSERT INTO users (username, password_hash, salt, pw_scheme, full_name,
              role, is_active, must_change_pw, teacher_id, school_id)
         VALUES (%s,%s,'','bcrypt',%s,%s,1,0,%s,1) ON CONFLICT (username) DO NOTHING""",
      (uname, pw_hash, f"{fn} {ln}", role, tid))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Students
# ─────────────────────────────────────────────────────────────────────────────
print("[5/12] Students (120)…")
MN = ["Juma","Ali","Hassan","Mohamed","Omar","David","Peter","John","Samuel",
      "Emmanuel","Joseph","Daniel","Robert","George","Michael","Patrick","Francis"]
FN = ["Fatuma","Amina","Zainab","Rehema","Aisha","Grace","Mary","Agnes","Rose",
      "Ruth","Sarah","Jane","Elizabeth","Faith","Joyce","Mercy","Charity"]
LN = ["Mwangi","Kimani","Hassan","Ochieng","Ndungu","Salim","Wanjiku","Mutua",
      "Ally","Juma","Chege","Omar","Kariuki","Kamau","Rashid","Moshi","Msangi",
      "Bakari","Hamisi","Rajabu","Mussa","Seif","Issa","Shaban","Dogo"]

adm_row = one("SELECT value FROM school_config WHERE key='student_adm_seq'")
seq = int(adm_row["value"]) if adm_row else 0
cls_list = list(CLS.values())
student_ids = []  # [(id, class_id)]

for i in range(1, 121):
    seq += 1
    adm_no = f"ADM/{YEAR}/{seq:04d}"
    gender = "Male" if i % 2 == 0 else "Female"
    fn = random.choice(MN if gender == "Male" else FN)
    ln = random.choice(LN)
    yr = YEAR - random.randint(13, 20)
    dob = f"{yr}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    cls_id = cls_list[(i - 1) % len(cls_list)]
    cat = random.choices(["regular","orphan","vulnerable"], weights=[80,12,8])[0]
    parent = f"{random.choice(MN)} {random.choice(LN)}"
    pphone = f"+2557{random.randint(10000000,99999999)}"
    x("""INSERT INTO students (admission_no, first_name, last_name, gender,
              date_of_birth, class_id, parent_name, parent_phone,
              student_category, student_type, is_active)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Day',1) ON CONFLICT DO NOTHING""",
      (adm_no, fn, ln, gender, dob, cls_id, parent, pphone, cat))
    r = one("SELECT id FROM students WHERE admission_no=%s", (adm_no,))
    if r: student_ids.append((r["id"], cls_id))

x("UPDATE school_config SET value=%s WHERE key='student_adm_seq'", (str(seq),))

# ─────────────────────────────────────────────────────────────────────────────
# 6. Fee Types & Structures
# ─────────────────────────────────────────────────────────────────────────────
print("[6/12] Fee types & structures…")
FEE_TYPES = [
    ("Tuition Fee",      1, 450000, "Annual school tuition"),
    ("Activity Fee",     1,  50000, "Sports, clubs, and activities"),
    ("Exam Fee",         1,  35000, "Examination registration"),
    ("Library Fee",      1,  20000, "Library access and resources"),
    ("ICT Fee",          1,  25000, "Computer lab and internet"),
    ("Development Levy", 1,  80000, "School development projects"),
]
ft_ids = {}
for name, term, amount, desc in FEE_TYPES:
    x("""INSERT INTO fee_types (name, term, amount, description)
         VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""", (name, term, amount, desc))
    r = one("SELECT id FROM fee_types WHERE name=%s", (name,))
    if r: ft_ids[name] = r["id"]

ROMAN = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6}
for cname, cid in CLS.items():
    form_num = ROMAN.get(cname.split()[1], 1)
    multiplier = 1.0 if form_num <= 4 else 1.3
    for fname, ftid in ft_ids.items():
        base = {"Tuition Fee":450000,"Activity Fee":50000,"Exam Fee":35000,
                "Library Fee":20000,"ICT Fee":25000,"Development Levy":80000}.get(fname, 30000)
        amount = int(base * multiplier)
        due = f"{YEAR}-04-01"
        x("""INSERT INTO fee_structures (class_id, fee_type_id, amount, academic_year_id, due_date)
             VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (cid, ftid, amount, AY, due))

# Generate student bills for each student
for sid, cls_id in student_ids:
    structs = all_(
        "SELECT id, amount FROM fee_structures WHERE class_id=%s AND academic_year_id=%s",
        (cls_id, AY))
    for s in structs:
        paid = random.choice([0, s["amount"] * 0.5, s["amount"]])
        status = "paid" if paid >= s["amount"] else ("partial" if paid > 0 else "unpaid")
        import hashlib, secrets as _sec
        ctrl = hashlib.sha256(f"{sid}-{s['id']}-{AY}".encode()).hexdigest()[:20].upper()
        x("""INSERT INTO student_bills (student_id, fee_structure_id, academic_year_id,
                  control_number, amount_due, amount_paid, status, due_date)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (sid, s["id"], AY, ctrl, s["amount"], paid, status, f"{YEAR}-04-01"))

# ─────────────────────────────────────────────────────────────────────────────
# 7. Exams & Grades
# ─────────────────────────────────────────────────────────────────────────────
print("[7/12] Exams & grades…")
EXAM_DEFS = [
    ("Term 1 Mid-Term", f"{YEAR}-02-20", f"{YEAR}-02-28"),
    ("Term 1 Final",    f"{YEAR}-03-20", f"{YEAR}-04-05"),
    ("Term 2 Mid-Term", f"{YEAR}-05-28", f"{YEAR}-06-05"),
    ("Term 2 Final",    f"{YEAR}-07-01", f"{YEAR}-07-15"),
]
exam_ids = []
for name, sd, ed in EXAM_DEFS:
    x("""INSERT INTO exams (name, academic_year_id, term, start_date, end_date, status)
         VALUES (%s,%s,1,%s,%s,'published') ON CONFLICT DO NOTHING""", (name, AY, sd, ed))
    r = one("SELECT id FROM exams WHERE name=%s AND academic_year_id=%s", (name, AY))
    if r: exam_ids.append(r["id"])

CORE = [SUBJ[c] for c in ["MATH","ENG","KIS","BIO","CHEM","PHY","HIST","GEO"] if c in SUBJ]
GRADE_MAP = [(90,"A"),(80,"B+"),(70,"B"),(60,"C"),(50,"D"),(0,"F")]

for exam_id in exam_ids[:2]:
    sample = random.sample(student_ids, min(80, len(student_ids)))
    for sid, _ in sample:
        for subj_id in CORE:
            score = random.gauss(65, 15)
            score = max(0, min(100, round(score)))
            letter = next(g for thresh, g in sorted(GRADE_MAP, reverse=True) if score >= thresh)
            x("""INSERT INTO grades (student_id, exam_id, subject_id, score, max_score,
                      grade_letter, status, entered_by)
                 VALUES (%s,%s,%s,%s,100,%s,'approved',1) ON CONFLICT DO NOTHING""",
              (sid, exam_id, subj_id, score, letter))

# ─────────────────────────────────────────────────────────────────────────────
# 8. Attendance (last 14 school days)
# ─────────────────────────────────────────────────────────────────────────────
print("[8/12] Attendance…")
for days_ago in range(1, 22):
    d = TODAY - datetime.timedelta(days=days_ago)
    if d.weekday() >= 5: continue
    for sid, cls_id in random.sample(student_ids, min(90, len(student_ids))):
        status = random.choices(["Present","Absent","Late"], weights=[87,8,5])[0]
        x("""INSERT INTO attendance (student_id, class_id, date, status, recorded_by)
             VALUES (%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
          (sid, cls_id, d.isoformat(), status))

# ─────────────────────────────────────────────────────────────────────────────
# 9. Library
# ─────────────────────────────────────────────────────────────────────────────
print("[9/12] Library…")
BOOKS = [
    ("New General Mathematics F4","J.B. Channon","978-0582600","textbook","Longman","2018","A1",4),
    ("Biology for O-Level","C.J. Clegg","978-0719578","textbook","Murray","2016","B2",4),
    ("Chemistry for O-Level","R.O.C. Norman","978-0582243","textbook","Longman","2017","C3",3),
    ("Physics for O-Level","Tom Duncan","978-0719572","textbook","Murray","2016","D4",4),
    ("History of East Africa","B.A. Ogot","978-9966460","textbook","EAPH","2015","E5",3),
    ("Geography for Tanzania","E. Mwombeki","978-9976100","textbook","TOAB","2019","F6",5),
    ("English Grammar in Use","Raymond Murphy","978-0521532","reference","Cambridge","2018","A2",6),
    ("Kiswahili Fasaha","TUKI","978-9976690","textbook","TUKI","2017","B3",5),
    ("Computer Studies F3","P.M. Heathcote","978-1904467","textbook","Payne-Gallway","2016","C4",3),
    ("Commerce O-Level","L. Whitehead","978-0582609","textbook","Longman","2018","D5",3),
    ("Principles of Accounts","F. Wood","978-0273685","textbook","Longman","2019","E6",3),
    ("Civics for Tanzania","MoE Tanzania","978-9976102","textbook","TOAB","2020","F1",4),
    ("Agriculture F1","C. Barker","978-0582279","textbook","Longman","2016","A3",3),
    ("The River Between","Ngugi wa Thiong'o","978-0435900","fiction","EAPH","2015","B4",2),
    ("Things Fall Apart","Chinua Achebe","978-0435901","fiction","Heinemann","2016","C5",3),
    ("Animal Farm","George Orwell","978-0141036","fiction","Penguin","2017","D6",3),
    ("Advanced Biology","M. Kent","978-0199148","reference","OUP","2018","E1",2),
    ("Statistics for A-Level","S.P. Gupta","978-8180548","textbook","Sultan Chand","2017","F2",2),
    ("Atlas for East Africa","Oxford Press","978-0195716","reference","OUP","2019","A4",2),
    ("Weep Not Child","Ngugi wa Thiong'o","978-0143039","fiction","Penguin","2016","B5",2),
]
book_ids = []
for title, author, isbn, cat, pub, yr, shelf, copies in BOOKS:
    x("""INSERT INTO library_books (title, author, isbn, category, publisher, year,
              shelf_location, total_copies, available_copies, is_active)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
      (title, author, isbn, cat, pub, yr, shelf, copies, copies))
    r = one("SELECT id FROM library_books WHERE isbn=%s", (isbn,))
    if r: book_ids.append(r["id"])

for i, (sid, _) in enumerate(random.sample(student_ids, min(18, len(student_ids)))):
    if i >= len(book_ids): break
    bid = book_ids[i]
    sname_r = one("SELECT first_name||' '||last_name AS n FROM students WHERE id=%s", (sid,))
    sname = sname_r["n"] if sname_r else "Student"
    due = (TODAY + datetime.timedelta(days=random.randint(3, 14))).isoformat()
    x("""INSERT INTO library_loans (book_id, borrower_type, borrower_id, borrower_name,
              issue_date, due_date, status, issued_by)
         VALUES (%s,'student',%s,%s,%s,%s,'active',1) ON CONFLICT DO NOTHING""",
      (bid, sid, sname, TODAY.isoformat(), due))  # status='active' per constraint
    x("UPDATE library_books SET available_copies=GREATEST(available_copies-1,0) WHERE id=%s", (bid,))

# ─────────────────────────────────────────────────────────────────────────────
# 10. Inventory
# ─────────────────────────────────────────────────────────────────────────────
print("[10/12] Inventory…")
ITEMS = [
    ("Whiteboard Markers (Box)", "stationery","Consumables","box",  2500, 45, 5, "StoreRoom A"),
    ("A4 Paper (Ream)",          "stationery","Consumables","ream", 8000, 30, 10,"StoreRoom A"),
    ("Staplers",                 "stationery","Equipment",  "pcs",  5000, 12, 3, "Office"),
    ("Manila Papers",            "stationery","Consumables","pcs",   500, 200,20, "StoreRoom A"),
    ("Ballpoint Pens (Box)",     "stationery","Consumables","box",  3000, 20, 5, "StoreRoom A"),
    ("Microscopes",              "equipment", "Lab",        "pcs", 250000,8,  2, "Biology Lab"),
    ("Bunsen Burners",           "equipment", "Lab",        "pcs",  35000,6,  2, "Chemistry Lab"),
    ("Beakers 250ml",            "equipment", "Lab",        "pcs",   8000,24, 5, "Chemistry Lab"),
    ("Test Tubes (Box)",         "equipment", "Lab",        "box",  15000, 10, 3, "Chemistry Lab"),
    ("Safety Goggles",           "equipment", "Safety",     "pcs",  12000, 30, 5, "Lab Store"),
    ("Football",                 "equipment", "Sports",     "pcs",  25000, 4,  2, "Sports Store"),
    ("Volleyball",               "equipment", "Sports",     "pcs",  22000, 3,  1, "Sports Store"),
    ("Basketball",               "equipment", "Sports",     "pcs",  30000, 2,  1, "Sports Store"),
    ("Scientific Calculators",   "equipment", "ICT",        "pcs",  35000, 25, 5, "ICT Room"),
    ("Computer Mice",            "equipment", "ICT",        "pcs",  15000, 18, 4, "ICT Room"),
    ("Extension Cables",         "equipment", "ICT",        "pcs",  20000, 10, 2, "ICT Room"),
    ("Brooms",                   "other",     "Maintenance","pcs",   3500, 15, 3, "Store"),
    ("Disinfectant (5L)",        "other",     "Maintenance","pcs",  18000, 8,  2, "Store"),
    ("First Aid Kits",           "equipment", "Health",     "pcs",  45000, 5,  2, "Sick Bay"),
    ("Notebooks (Box of 10)",    "stationery","Consumables","box",  12000, 50, 10,"StoreRoom A"),
]
for name, mcat, subcat, unit, price, qty, reorder, loc in ITEMS:
    x("""INSERT INTO inventory_items (name, main_category, subcategory, unit, unit_price,
              stock_qty, reorder_qty, location, is_active, status)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,'available') ON CONFLICT DO NOTHING""",
      (name, mcat, subcat, unit, price, qty, reorder, loc))

# ─────────────────────────────────────────────────────────────────────────────
# 11. Transport Routes
# ─────────────────────────────────────────────────────────────────────────────
print("[11/12] Transport & payroll…")
ROUTES = [
    ("Route A – Arusha Town",  "Arusha Town centre",  "T 123 AAA","Hamisi Mwangi","+255755001001",25000,25000,25000),
    ("Route B – Moshi Road",   "Moshi/Himo area",     "T 456 BBB","Omar Salim",   "+255755001002",35000,35000,35000),
    ("Route C – Tengeru",      "Tengeru/Usa River",   "T 789 CCC","Peter Kimani", "+255755001003",20000,20000,20000),
    ("Route D – Njiro",        "Njiro/Sakina area",   "T 012 DDD","John Hassan",  "+255755001004",15000,15000,15000),
]
for name, desc, vno, drv, dph, f1, f2, f3 in ROUTES:
    x("""INSERT INTO transport_routes (name, description, vehicle_no, driver_name,
              driver_phone, fare_term1, fare_term2, fare_term3, is_active)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
      (name, desc, vno, drv, dph, f1, f2, f3))

# Payroll salary config
all_t = all_("SELECT id FROM teachers")
for t in all_t:
    basic = random.choice([650000,750000,850000,950000,1100000,1300000])
    x("""INSERT INTO payroll_salary_config
              (teacher_id, basic_salary, housing_allow, transport_allow, other_allow,
               loan_deduction, loan_board)
         VALUES (%s,%s,%s,%s,%s,0,0) ON CONFLICT (teacher_id) DO NOTHING""",
      (t["id"], basic, basic*0.15, 50000, 0))

# ─────────────────────────────────────────────────────────────────────────────
# 12. Expenses, Welfare & Health
# ─────────────────────────────────────────────────────────────────────────────
print("[12/12] Expenses, welfare & health…")
EXP_CATS = [("Utilities","EXP-UTL"),("Maintenance","EXP-MNT"),("Office Supplies","EXP-OFF"),
            ("Transport","EXP-TRN"),("Catering","EXP-CAT"),("Security","EXP-SEC")]
for cname, code in EXP_CATS:
    x("INSERT INTO expense_categories (name, account_code) VALUES (%s,%s) ON CONFLICT DO NOTHING",
      (cname, code))

# category must be one of: salaries, utilities, supplies, maintenance, transport, welfare, other
EXP_ROWS = [
    ("utilities",   "Electricity bill – TANESCO",          320000),
    ("utilities",   "Water bill – AUWSA",                  85000),
    ("maintenance", "Classroom roof repair – Block B",      450000),
    ("maintenance", "Plumbing works – toilets",             180000),
    ("maintenance", "Painting of dormitory walls",          260000),
    ("supplies",    "Stationery purchase – Term 1",         95000),
    ("supplies",    "Lab chemicals and reagents",           210000),
    ("supplies",    "Sports equipment replacement",         175000),
    ("supplies",    "Cleaning materials",                   55000),
    ("transport",   "School bus fuel – Term 1",             380000),
    ("transport",   "Bus service contract – Route A",       250000),
    ("transport",   "Field trip transport",                 120000),
    ("salaries",    "Support staff salaries – January",    850000),
    ("salaries",    "Guard company monthly fee",            180000),
    ("welfare",     "Student bursary fund disbursement",    300000),
    ("welfare",     "Sanitary products for needy students",  45000),
    ("other",       "Parent-teacher meeting refreshments",   35000),
    ("other",       "School signage printing",               60000),
    ("other",       "External exam centre registration",    125000),
    ("other",       "School event decoration",               40000),
]
for cat, desc, amt in EXP_ROWS:
    d = (TODAY - datetime.timedelta(days=random.randint(1, 90))).isoformat()
    x("""INSERT INTO expenses (category, description, amount, expense_date, recorded_by)
         VALUES (%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""", (cat, desc, amt, d))

# Welfare records
for sid, _ in random.sample(student_ids, min(12, len(student_ids))):
    cat  = random.choice(["orphan","half_orphan","vulnerable","sponsored"])
    supp = random.choice(["full_fees","partial","non_financial"])
    x("""INSERT INTO welfare_records (student_id, category, support_type, verified, notes)
         VALUES (%s,%s,%s,0,'Student identified as requiring support') ON CONFLICT DO NOTHING""",
      (sid, cat, supp))

# Health visits
SYMPTOMS = ["Headache and fever","Stomach pain","Dizziness","Eye irritation",
            "Knee injury from sports","Toothache","Skin rash","Cough and cold"]
TREATMENTS = ["Paracetamol prescribed, rest advised","Oral rehydration, parent notified",
              "Dressing applied, referred to hospital","Antihistamine prescribed",
              "Ice pack applied, parent contacted","Referred to dental clinic"]
for sid, _ in random.sample(student_ids, min(25, len(student_ids))):
    d   = (TODAY - datetime.timedelta(days=random.randint(1, 45))).isoformat()
    sym = random.choice(SYMPTOMS)
    trm = random.choice(TREATMENTS)
    action = random.choice(["treated","referred","rest","other"])
    x("""INSERT INTO health_visits (student_id, visit_date, symptoms, treatment,
              action_taken, parent_notified, created_by)
         VALUES (%s,%s,%s,%s,%s,0,1) ON CONFLICT DO NOTHING""", (sid, d, sym, trm, action))

# ─────────────────────────────────────────────────────────────────────────────
conn.commit(); cur.close(); conn.close()

print("\n=== Done! ===")
print(f"  Classes     : {len(CLS)}")
print(f"  Subjects    : {len(SUBJ)}")
print(f"  Teachers    : {len(all_t) if 'all_t' in dir() else len(TEACHERS)}")
print(f"  Students    : {len(student_ids)}")
print(f"  Library     : {len(book_ids)} books")
print(f"  Inventory   : {len(ITEMS)} items")
print(f"\n  Teacher login password: Teacher@2025")
