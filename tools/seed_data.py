"""
Seed realistic demo data for Kibandani Primary School.
Run: python tools/seed_data.py
"""
import sqlite3, hashlib, secrets, random, datetime, sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "school_mis.db"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()


# ── helpers ──────────────────────────────────────────────────────────────────

def hp(pw):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + pw).encode()).hexdigest()
    return h, salt

def ins(sql, params=()):
    cur.execute(sql, params)
    return cur.lastrowid

def rand_date(start_year, end_year):
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y:04d}-{m:02d}-{d:02d}"

def date_offset(days):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

def past_date(days_ago):
    return (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()

today = datetime.date.today().isoformat()
year = datetime.date.today().year

print("Seeding Kibandani Primary School demo data…")

# ── 1. Academic years ─────────────────────────────────────────────────────────
ay_prev = ins("""INSERT OR IGNORE INTO academic_years (label,start_date,end_date,is_current) VALUES (?,?,?,?)""",
              (f"{year-1}", f"{year-1}-01-15", f"{year-1}-11-30", 0))
ay_id = ins("""INSERT OR IGNORE INTO academic_years (label,start_date,end_date,is_current) VALUES (?,?,?,?)""",
            (f"{year}", f"{year}-01-10", f"{year}-11-28", 1))
# get real IDs in case of IGNORE
ay_prev = cur.execute(f"SELECT id FROM academic_years WHERE label='{year-1}'").fetchone()[0]
ay_id   = cur.execute(f"SELECT id FROM academic_years WHERE label='{year}'").fetchone()[0]

# ── 2. Terms ──────────────────────────────────────────────────────────────────
for t_name, t_start, t_end, t_cur in [
    ("Term 1", f"{year}-01-10", f"{year}-03-28", 0),
    ("Term 2", f"{year}-04-14", f"{year}-07-25", 1),
    ("Term 3", f"{year}-08-11", f"{year}-11-28", 0),
]:
    cur.execute("""INSERT OR IGNORE INTO terms (academic_year_id,name,start_date,end_date,is_current) VALUES (?,?,?,?,?)""",
                (ay_id, t_name, t_start, t_end, t_cur))

conn.commit()
print("  ✓ Academic years & terms")

# ── 3. Subjects ───────────────────────────────────────────────────────────────
subjects_data = [
    ("Kiswahili",         "KSW", None, "compulsory"),
    ("English",           "ENG", None, "compulsory"),
    ("Mathematics",       "MTH", None, "compulsory"),
    ("Science",           "SCI", None, "compulsory"),
    ("Social Studies",    "SST", None, "compulsory"),
    ("Religious Studies", "REL", None, "compulsory"),
    ("Physical Education","PED", None, "compulsory"),
    ("Art & Craft",       "ART", None, "elective"),
    ("Computer Studies",  "CMP", None, "elective"),
    ("Agriculture",       "AGR", None, "elective"),
]
subj_ids = {}
for name, code, gl, stype in subjects_data:
    cur.execute("INSERT OR IGNORE INTO subjects (name,code,subject_type) VALUES (?,?,?)", (name, code, stype))
    row = cur.execute("SELECT id FROM subjects WHERE code=?", (code,)).fetchone()
    subj_ids[code] = row[0]

conn.commit()
print("  ✓ Subjects")

# ── 4. Teachers ───────────────────────────────────────────────────────────────
teachers_raw = [
    ("Amina",    "Juma",     "Female", "0712345601", "amina.juma@kibandani.sc.tz",   "Mathematics",       "B.Ed Mathematics",     f"{year-1}-01-15", f"EMP/{year}/0001"),
    ("Charles",  "Mwamba",   "Male",   "0712345602", "charles.mwamba@kibandani.sc.tz","English",           "B.Ed English",         f"{year-3}-03-01", f"EMP/{year}/0002"),
    ("Fatuma",   "Hassan",   "Female", "0712345603", "fatuma.hassan@kibandani.sc.tz", "Kiswahili",         "Dip. Education",       f"{year-5}-06-12", f"EMP/{year}/0003"),
    ("George",   "Kimani",   "Male",   "0712345604", "george.kimani@kibandani.sc.tz", "Science",           "B.Sc Education",       f"{year-2}-01-08", f"EMP/{year}/0004"),
    ("Halima",   "Bakari",   "Female", "0712345605", "halima.bakari@kibandani.sc.tz", "Social Studies",    "B.Ed Humanities",      f"{year-4}-09-20", f"EMP/{year}/0005"),
    ("Ibrahim",  "Salim",    "Male",   "0712345606", "ibrahim.salim@kibandani.sc.tz", "Physical Education","Cert. P.E.",            f"{year-1}-03-05", f"EMP/{year}/0006"),
    ("Joyce",    "Nyamori",  "Female", "0712345607", "joyce.nyamori@kibandani.sc.tz", "Mathematics",       "B.Ed Mathematics",     f"{year-6}-08-15", f"EMP/{year}/0007"),
    ("Kelvin",   "Otieno",   "Male",   "0712345608", "kelvin.otieno@kibandani.sc.tz", "Computer Studies",  "B.Sc Computer Science",f"{year-2}-02-28", f"EMP/{year}/0008"),
    ("Leila",    "Mohamed",  "Female", "0712345609", "leila.mohamed@kibandani.sc.tz", "Art & Craft",       "Dip. Fine Arts",       f"{year-3}-07-01", f"EMP/{year}/0009"),
    ("Martin",   "Waweru",   "Male",   "0712345610", "martin.waweru@kibandani.sc.tz", "Agriculture",       "B.Sc Agri-Education",  f"{year-7}-01-10", f"EMP/{year}/0010"),
    ("Naomi",    "Ochieng",  "Female", "0712345611", None,                            "English",           "B.Ed English",         f"{year-1}-09-01", f"EMP/{year}/0011"),
    ("Patrick",  "Abuya",    "Male",   "0712345612", None,                            "Kiswahili",         "Dip. Education",       f"{year-2}-04-15", f"EMP/{year}/0012"),
    ("Rita",     "Muthomi",  "Female", "0712345613", None,                            "Science",           "B.Ed Science",         f"{year-3}-11-10", f"EMP/{year}/0013"),
    ("Samuel",   "Ndegwa",   "Male",   "0712345614", None,                            "Mathematics",       "M.Ed Mathematics",     f"{year-8}-01-03", f"EMP/{year}/0014"),
]

teacher_ids = []
for fn, ln, gd, ph, em, spec, qual, jd, emp_no in teachers_raw:
    cur.execute("""INSERT OR IGNORE INTO teachers
        (first_name,last_name,gender,phone,email,subject_specialization,qualification,joining_date,employee_no,is_active)
        VALUES (?,?,?,?,?,?,?,?,?,1)""",
        (fn, ln, gd, ph, em, spec, qual, jd, emp_no))
    row = cur.execute("SELECT id FROM teachers WHERE employee_no=?", (emp_no,)).fetchone()
    teacher_ids.append(row[0])

# Update sequence counter
cur.execute("UPDATE school_config SET value='14' WHERE key='teacher_emp_seq'")
conn.commit()
print(f"  ✓ {len(teacher_ids)} teachers")

# ── 5. Classes (Standard 1–7, two streams A/B) ────────────────────────────────
class_defs = [
    ("Std 1A", 1), ("Std 1B", 1),
    ("Std 2A", 2), ("Std 2B", 2),
    ("Std 3A", 3), ("Std 3B", 3),
    ("Std 4A", 4), ("Std 4B", 4),
    ("Std 5A", 5), ("Std 5B", 5),
    ("Std 6A", 6), ("Std 6B", 6),
    ("Std 7A", 7), ("Std 7B", 7),
]
class_ids = {}
for i, (cname, glevel) in enumerate(class_defs):
    tid = teacher_ids[i % len(teacher_ids)]
    cur.execute("""INSERT OR IGNORE INTO classes
        (name,grade_level,academic_year_id,teacher_id,capacity)
        VALUES (?,?,?,?,?)""",
        (cname, glevel, ay_id, tid, 45))
    row = cur.execute("SELECT id FROM classes WHERE name=? AND academic_year_id=?", (cname, ay_id)).fetchone()
    class_ids[cname] = row[0]

conn.commit()
print(f"  ✓ {len(class_ids)} classes")

# ── 6. Students ───────────────────────────────────────────────────────────────
FIRST_M = ["Juma","Bakari","Hassan","Said","Omar","Ali","Hamisi","Rashid","Salim","Ismail",
           "David","John","Peter","Paul","Joseph","Michael","Daniel","Samuel","George","Robert",
           "Kevin","Brian","Dennis","Mark","Simon","Patrick","Charles","James","Edward","Andrew"]
FIRST_F = ["Fatuma","Amina","Zainab","Maryam","Khadija","Halima","Safia","Rehema","Aisha","Leila",
           "Mary","Grace","Faith","Mercy","Joyce","Esther","Eunice","Agnes","Rose","Beatrice",
           "Alice","Jane","Susan","Ann","Catherine","Naomi","Ruth","Lydia","Priscilla","Deborah"]
LAST    = ["Juma","Mwamba","Hassan","Kimani","Bakari","Salim","Otieno","Waweru","Ndegwa","Abuya",
           "Muthomi","Ochieng","Mohamed","Nyamori","Msechu","Ngoma","Kamau","Kariuki","Mutua","Mwangi",
           "Odhiambo","Owino","Auma","Akello","Namukasa","Nanyondo","Ssemakula","Kiprotich","Ruto","Korir"]

students_per_class = 35
total_students = 0
student_seq = cur.execute("SELECT value FROM school_config WHERE key='student_adm_seq'").fetchone()
seq_counter = int(student_seq[0]) if student_seq else 0

student_ids_by_class = {}

random.seed(42)
for cname, cid in class_ids.items():
    class_students = []
    grade_level = int(cname.split(" ")[1][0])  # extract digit from "Std 3A"
    dob_year_range = (year - grade_level - 8, year - grade_level - 6)

    for _ in range(students_per_class):
        gender = random.choice(["Male", "Female"])
        fn = random.choice(FIRST_M if gender == "Male" else FIRST_F)
        ln = random.choice(LAST)
        seq_counter += 1
        adm_no = f"ADM/{year}/{seq_counter:04d}"
        dob = rand_date(*dob_year_range)
        parent_name = random.choice(FIRST_M) + " " + ln
        parent_phone = f"07{random.randint(10000000,99999999)}"
        cat = random.choices(
            ["regular","regular","regular","regular","regular","orphan","orphan","sponsored"],
            k=1
        )[0]
        row_id = cur.execute("""INSERT INTO students
            (admission_no,first_name,last_name,gender,date_of_birth,class_id,
             parent_name,parent_phone,student_category,is_active)
            VALUES (?,?,?,?,?,?,?,?,?,1)""",
            (adm_no, fn, ln, gender, dob, cid, parent_name, parent_phone, cat)).lastrowid
        class_students.append(row_id)
        total_students += 1

    student_ids_by_class[cname] = class_students

# update counter
cur.execute("UPDATE school_config SET value=? WHERE key='student_adm_seq'", (str(seq_counter),))
conn.commit()
print(f"  ✓ {total_students} students across {len(class_ids)} classes")

# ── 7. Guardians ─────────────────────────────────────────────────────────────
random.seed(99)
guardian_count = 0
for cname, sids in student_ids_by_class.items():
    for sid in sids[:10]:  # first 10 per class get full guardian records
        row = cur.execute("SELECT parent_name,parent_phone FROM students WHERE id=?", (sid,)).fetchone()
        gid = ins("""INSERT INTO guardians
            (full_name,relationship,phone,is_emergency_contact,is_pickup_authorized)
            VALUES (?,?,?,1,1)""",
            (row[0], random.choice(["father","mother","guardian"]), row[1]))
        ins("INSERT OR IGNORE INTO guardian_students (guardian_id,student_id,is_primary) VALUES (?,?,1)",
            (gid, sid))
        guardian_count += 1

conn.commit()
print(f"  ✓ {guardian_count} guardian records")

# ── 8. Enrollments ────────────────────────────────────────────────────────────
admin_row = cur.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
if admin_row:
    admin_uid = admin_row[0]
else:
    h, salt = hp("admin123")
    cur.execute("INSERT OR IGNORE INTO users (username,password_hash,salt,role,full_name,is_active) VALUES ('admin',?,?,'admin','Administrator',1)", (h, salt))
    conn.commit()
    admin_uid = cur.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]

for cname, cid in class_ids.items():
    for sid in student_ids_by_class[cname]:
        cur.execute("""INSERT OR IGNORE INTO enrollments
            (student_id,class_id,academic_year_id,status,created_by)
            VALUES (?,?,?,'active',?)""",
            (sid, cid, ay_id, admin_uid))

conn.commit()
print(f"  ✓ Enrollments created")

# ── 9. Fee types & structures ────────────────────────────────────────────────
fee_types_data = [
    ("Tuition Fee",       50000, None, "Main term tuition"),
    ("Activity Fee",      10000, None, "Sports, clubs, activities"),
    ("Library Fee",        5000, None, "Library access and materials"),
    ("Exam Fee",           8000, None, "Examination and marking"),
    ("Development Fund",  15000, None, "School infrastructure"),
    ("Uniform Fee",       25000, 1,    "School uniform (Term 1 only)"),
    ("Transport Fee",     30000, None, "Bus/van transport"),
]
fee_type_ids = {}
for name, amt, term, desc in fee_types_data:
    cur.execute("INSERT OR IGNORE INTO fee_types (name,amount,term,description) VALUES (?,?,?,?)",
                (name, amt, term, desc))
    row = cur.execute("SELECT id FROM fee_types WHERE name=?", (name,)).fetchone()
    fee_type_ids[name] = row[0]

# Fee structures for each class
for cname, cid in class_ids.items():
    for fname, amt, term, _ in fee_types_data:
        if fname == "Transport Fee":
            continue  # handled separately
        ft_id = fee_type_ids[fname]
        for t in ([term] if term else [1, 2, 3]):
            due = f"{year}-0{t}-28" if t < 10 else f"{year}-{t}-28"
            cur.execute("""INSERT OR IGNORE INTO fee_structures
                (academic_year_id,class_id,fee_type_id,amount,term,due_date)
                VALUES (?,?,?,?,?,?)""",
                (ay_id, cid, ft_id, amt, t, due))

conn.commit()
print(f"  ✓ Fee types & structures")

# ── 10. Student bills (fee charges) ──────────────────────────────────────────
bill_count = 0
random.seed(7)
for cname, cid in class_ids.items():
    for sid in student_ids_by_class[cname]:
        # Bill for tuition term 2 (current term)
        cur.execute("""INSERT OR IGNORE INTO student_bills
            (student_id,fee_structure_id,academic_year_id,amount_due,amount_paid,due_date,status)
            SELECT ?,fs.id,?,fs.amount,?,fs.due_date,?
            FROM fee_structures fs
            WHERE fs.class_id=? AND fs.academic_year_id=? AND fs.term=2
            AND NOT EXISTS (SELECT 1 FROM student_bills sb WHERE sb.student_id=? AND sb.fee_structure_id=fs.id)
            """, (sid, ay_id,
                  random.choice([0, 0, 0, 50000, 25000, 50000]),  # some paid
                  random.choice(['unpaid','paid','partial']),
                  cid, ay_id, sid))
        bill_count += 1

conn.commit()
print(f"  ✓ Student bills created")

# ── 11. Exams ────────────────────────────────────────────────────────────────
exams_data = [
    (f"Term 1 Exam {year}",    ay_id, 1, f"{year}-03-18", f"{year}-03-22", "published"),
    (f"Mid Term 2 Exam {year}", ay_id, 2, f"{year}-05-19", f"{year}-05-21", "published"),
    (f"Term 2 Exam {year}",    ay_id, 2, f"{year}-07-14", f"{year}-07-18", "open"),
    (f"Term 3 Exam {year}",    ay_id, 3, f"{year}-11-17", f"{year}-11-21", "open"),
]
exam_ids = []
for ename, ayi, t, sd, ed, status in exams_data:
    cur.execute("""INSERT OR IGNORE INTO exams (name,academic_year_id,term,start_date,end_date,status)
        VALUES (?,?,?,?,?,?)""", (ename, ayi, t, sd, ed, status))
    row = cur.execute("SELECT id FROM exams WHERE name=?", (ename,)).fetchone()
    exam_ids.append(row[0])

conn.commit()
print(f"  ✓ {len(exam_ids)} exams")

# ── 12. Grades (for published exams) ─────────────────────────────────────────
core_subjects = ["KSW","ENG","MTH","SCI","SST","REL"]
grade_count = 0
random.seed(55)
teacher_uid = admin_uid

for exam_id in exam_ids[:2]:  # Term 1 + Mid Term 2 (published)
    exam_row = cur.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    for cname, cid in class_ids.items():
        for sid in student_ids_by_class[cname]:
            for scode in core_subjects:
                subj_id = subj_ids[scode]
                score = round(random.gauss(65, 18), 1)
                score = max(0, min(100, score))
                if score >= 80:   gl = "A"
                elif score >= 65: gl = "B"
                elif score >= 50: gl = "C"
                elif score >= 40: gl = "D"
                else:             gl = "F"
                try:
                    cur.execute("""INSERT OR IGNORE INTO grades
                        (student_id,exam_id,subject_id,class_id,score,max_score,grade_letter,
                         status,entered_by,approved_by)
                        VALUES (?,?,?,?,?,100,?,?,?,?)""",
                        (sid, exam_id, subj_id, cid, score, gl,
                         "approved" if exam_row["status"]=="published" else "draft",
                         admin_uid, admin_uid))
                    grade_count += 1
                except Exception:
                    pass

    if grade_count % 1000 == 0:
        conn.commit()

conn.commit()
print(f"  ✓ {grade_count} grade records")

# ── 13. Attendance (last 30 school days) ─────────────────────────────────────
att_count = 0
random.seed(33)
school_days = []
d = datetime.date.today()
while len(school_days) < 30:
    d -= datetime.timedelta(days=1)
    if d.weekday() < 5:  # Mon-Fri
        school_days.append(d.isoformat())

for cname, cid in class_ids.items():
    for sid in student_ids_by_class[cname][:20]:  # first 20 per class
        for att_date in school_days[-10:]:          # last 10 days
            status = random.choices(
                ["Present","Present","Present","Present","Absent","Late"],
                k=1
            )[0]
            cur.execute("""INSERT OR IGNORE INTO attendance
                (student_id,class_id,date,status,recorded_by)
                VALUES (?,?,?,?,?)""",
                (sid, cid, att_date, status, admin_uid))
            att_count += 1

conn.commit()
print(f"  ✓ {att_count} attendance records")

# ── 14. Health visits ─────────────────────────────────────────────────────────
complaints = [
    ("Headache, fever",         "Malaria",          "Paracetamol 500mg",    "treated",    "Nurse Zawadi"),
    ("Stomach pain, vomiting",  "Gastroenteritis",  "ORS, rest",            "sent_home",  "Nurse Zawadi"),
    ("Cough, running nose",     "Common Cold",      "Antihistamine",        "treated",    "Nurse Baraka"),
    ("Eye pain, itching",       "Conjunctivitis",   "Eye drops",            "treated",    "Nurse Zawadi"),
    ("Wound on knee",           "Laceration",       "Antiseptic, bandage",  "treated",    "Nurse Baraka"),
    ("Dizziness, weakness",     "Anaemia (suspected)","Iron supplement",    "referred",   "Nurse Zawadi"),
    ("Chest pain, difficulty breathing","Asthma",   "Inhaler, rest",        "referred",   "Nurse Baraka"),
    ("Toothache",               "Dental caries",    "Pain relief",          "referred",   "Nurse Zawadi"),
]
health_count = 0
random.seed(11)
all_students = [sid for sids in student_ids_by_class.values() for sid in sids]

for i in range(80):
    sid = random.choice(all_students)
    days_ago = random.randint(1, 90)
    comp = random.choice(complaints)
    notified = random.choice([0, 1])
    cur.execute("""INSERT INTO health_visits
        (student_id,visit_date,symptoms,diagnosis,treatment,action_taken,
         parent_notified,nurse_name,created_by)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (sid, past_date(days_ago), comp[0], comp[1], comp[2], comp[3],
         notified, comp[4], admin_uid))
    health_count += 1

conn.commit()
print(f"  ✓ {health_count} health visit records")

# ── 15. Welfare records ───────────────────────────────────────────────────────
welfare_count = 0
random.seed(22)
for cname, sids in student_ids_by_class.items():
    for sid in sids:
        row = cur.execute("SELECT student_category FROM students WHERE id=?", (sid,)).fetchone()
        cat = row[0]
        if cat in ("orphan","sponsored"):
            welfare_cat = "orphan" if cat == "orphan" else "sponsored"
            sponsor_name = "Rotary Club Mombasa" if cat == "sponsored" else None
            cur.execute("""INSERT OR IGNORE INTO welfare_records
                (student_id,category,is_current,verified,support_type,sponsor_name,notes)
                VALUES (?,?,1,1,?,?,?)""",
                (sid, welfare_cat,
                 "full_fees" if cat == "sponsored" else "non_financial",
                 sponsor_name,
                 f"Verified by head teacher on {past_date(30)}"))
            welfare_count += 1

conn.commit()
print(f"  ✓ {welfare_count} welfare records")

# ── 16. Library books ────────────────────────────────────────────────────────
books_data = [
    ("Kiswahili Darasa la 4",     "TUKI", "978-9976-6",  "textbook",    "Shelf A1", 10, 7),
    ("English for Today Std 5",   "OUP",  "978-0-19-5",  "textbook",    "Shelf A2", 8,  5),
    ("Mathematics Book 6",        "EPB",  "978-9987-0",  "textbook",    "Shelf A3", 12, 10),
    ("Science & Technology Std 7","Longhorn","978-9966-", "textbook",   "Shelf A4", 6,  3),
    ("The Pearl",                 "John Steinbeck","978-0","fiction",   "Shelf B1", 4,  4),
    ("Animal Farm",               "George Orwell","978-0-","fiction",   "Shelf B2", 3,  2),
    ("Oxford Primary Dictionary", "OUP",  "978-0-19-0",  "reference",   "Shelf C1", 5,  4),
    ("Encyclopaedia Britannica (Primary)","Britannica","","reference",  "Shelf C2", 2,  2),
    ("Healthy Living for Children","MoH", "978-9987-1",  "non_fiction", "Shelf D1", 6,  6),
    ("Our Environment",           "EPB",  "978-9987-2",  "non_fiction", "Shelf D2", 4,  3),
    ("Story of Africa",           "EPB",  "978-9987-3",  "non_fiction", "Shelf D3", 5,  5),
    ("Tales from East Africa",    "EPB",  "978-9987-4",  "fiction",     "Shelf B3", 8,  6),
    ("Fun with Numbers",          "EPB",  "978-9987-5",  "textbook",    "Shelf A5", 7,  7),
    ("Primary Social Studies 7",  "Longhorn","978-9966-2","textbook",   "Shelf A6", 9,  8),
    ("The Elephant's Child",      "Kipling","978-0-14-",  "fiction",     "Shelf B4", 3,  3),
    ("Science Experiments at Home","Various","978-9987-6","non_fiction","Shelf D4", 4,  4),
    ("World Atlas for Schools",   "OUP",  "978-0-19-6",  "reference",   "Shelf C3", 3,  3),
    ("Hadithi za Kiswahili",      "EPB",  "978-9987-7",  "fiction",     "Shelf B5", 6,  5),
    ("HIV/AIDS Education",        "MoH",  "978-9987-8",  "non_fiction", "Shelf D5", 5,  5),
    ("Primary Mathematics Rev.",  "EPB",  "978-9987-9",  "textbook",    "Shelf A7", 10, 9),
]
for title, author, isbn, cat, shelf, total, avail in books_data:
    cur.execute("""INSERT OR IGNORE INTO library_books
        (title,author,isbn,category,shelf_location,total_copies,available_copies)
        VALUES (?,?,?,?,?,?,?)""",
        (title, author, isbn, cat, shelf, total, avail))

conn.commit()
print(f"  ✓ {len(books_data)} library books")

# ── 17. Library loans ─────────────────────────────────────────────────────────
book_ids = [r[0] for r in cur.execute("SELECT id FROM library_books").fetchall()]
loan_count = 0
random.seed(44)
for i in range(40):
    sid = random.choice(all_students)
    bid = random.choice(book_ids)
    days_ago = random.randint(2, 25)
    due_days  = days_ago - random.randint(7, 14)
    returned  = random.choice([True, False, False])
    student_row = cur.execute("SELECT first_name,last_name FROM students WHERE id=?", (sid,)).fetchone()
    bname = f"{student_row[0]} {student_row[1]}" if student_row else "Student"
    try:
        cur.execute("""INSERT INTO library_loans
            (book_id,borrower_type,borrower_id,borrower_name,issue_date,due_date,return_date,status,issued_by)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (bid, "student", sid, bname,
             past_date(days_ago),
             past_date(due_days) if due_days > 0 else date_offset(abs(due_days)),
             past_date(1) if returned else None,
             "returned" if returned else "active",
             admin_uid))
        loan_count += 1
    except Exception:
        pass

conn.commit()
print(f"  ✓ {loan_count} library loans")

# ── 18. Transport routes ──────────────────────────────────────────────────────
routes_data = [
    ("Route A – Makadara",  "Makadara → Mji Mpya → School",  "T 123 AAA", "Musa Hamisi",  "0756111001", 20000, 20000, 20000),
    ("Route B – Mbagala",   "Mbagala → Kigamboni → School",  "T 456 BBB", "Ali Omar",     "0756111002", 22000, 22000, 22000),
    ("Route C – Kimara",    "Kimara → Tabata → School",       "T 789 CCC", "John Mwangi",  "0756111003", 25000, 25000, 25000),
    ("Route D – Gongo la Mboto","Gongo la Mboto → School",   "T 321 DDD", "Said Baraka",  "0756111004", 18000, 18000, 18000),
]
for name, desc, veh, drv, dph, f1, f2, f3 in routes_data:
    cur.execute("""INSERT OR IGNORE INTO transport_routes
        (name,description,vehicle_no,driver_name,driver_phone,fare_term1,fare_term2,fare_term3)
        VALUES (?,?,?,?,?,?,?,?)""",
        (name, desc, veh, drv, dph, f1, f2, f3))

conn.commit()
print(f"  ✓ Transport routes")

# ── 19. System users ──────────────────────────────────────────────────────────
users_to_add = [
    # (username,   password,    role,              full_name,             teacher_idx)
    ("head",       "Head@1234", "head_teacher",    "Mrs. Joyce Nyamori",  6),  # teacher index 6
    ("academic",   "Acad@1234", "academic",        "Mr. Samuel Ndegwa",   13),
    ("accountant", "Acct@1234", "accountant",      "Ms. Rita Muthomi",    12),
    ("welfare",    "Welf@1234", "welfare_officer", "Ms. Halima Bakari",   4),
    ("librarian",  "Lib@1234",  "subject_teacher", "Mr. Kelvin Otieno",   7),
    ("teacher1",   "Teach@123", "class_teacher",   "Ms. Amina Juma",      0),
    ("teacher2",   "Teach@123", "class_teacher",   "Mr. Charles Mwamba",  1),
    ("teacher3",   "Teach@123", "subject_teacher", "Ms. Fatuma Hassan",   2),
]
new_user_count = 0
for uname, pw, role, fullname, tidx in users_to_add:
    exists = cur.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
    if exists:
        continue
    h, salt = hp(pw)
    tid = teacher_ids[tidx] if tidx < len(teacher_ids) else None
    cur.execute("""INSERT INTO users
        (username,password_hash,salt,role,full_name,teacher_id,is_active,must_change_pw)
        VALUES (?,?,?,?,?,?,1,0)""",
        (uname, h, salt, role, fullname, tid))
    new_user_count += 1

conn.commit()
print(f"  ✓ {new_user_count} new user accounts created")

# ── 20. School config / name ──────────────────────────────────────────────────
cur.execute("INSERT OR IGNORE INTO school_config (key,value) VALUES ('school_name','Kibandani Primary School')")
cur.execute("INSERT OR IGNORE INTO school_config (key,value) VALUES ('school_address','P.O. Box 1234, Kibandani, Pwani Region, Tanzania')")
cur.execute("INSERT OR IGNORE INTO school_config (key,value) VALUES ('school_phone','0222 123456')")
cur.execute("INSERT OR IGNORE INTO school_config (key,value) VALUES ('school_email','info@kibandani.sc.tz')")
cur.execute("INSERT OR IGNORE INTO school_config (key,value) VALUES ('currency','TZS')")
conn.commit()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\nSeed complete! Database summary:")
for table in ["users","teachers","classes","students","enrollments","subjects",
              "exams","grades","attendance","health_visits","welfare_records",
              "library_books","library_loans","transport_routes","fee_types","fee_structures"]:
    n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table:25s}  {n:>6}")

print(f"""
Login credentials
─────────────────
  admin      / admin123   (existing)
  head       / Head@1234  (head teacher)
  academic   / Acad@1234  (academic officer)
  accountant / Acct@1234  (accountant)
  welfare    / Welf@1234  (welfare officer)
  teacher1   / Teach@123  (class teacher)
  teacher2   / Teach@123  (class teacher)
  teacher3   / Teach@123  (subject teacher)
""")

conn.close()
