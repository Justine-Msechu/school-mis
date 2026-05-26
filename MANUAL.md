# School MIS — User Manual

**Version 2.2 | Web Edition**

This manual covers everything from first-time setup to daily use of every module.
Work through the sections in order the first time — each section builds on the previous one.

---

## Table of Contents

1. [How the System Works](#1-how-the-system-works)
2. [First-Time Setup (Setup Wizard)](#2-first-time-setup-setup-wizard)
3. [Settings — Configure Before Anything Else](#3-settings--configure-before-anything-else)
   - 3.1 School Information
   - 3.2 Academic Years
   - 3.3 Subjects
   - 3.4 User Accounts & Roles
4. [Classes](#4-classes)
5. [Teachers](#5-teachers)
6. [Students](#6-students)
7. [Guardians](#7-guardians)
8. [Enrollment](#8-enrollment)
9. [Attendance](#9-attendance)
10. [Grades & Exams](#10-grades--exams)
11. [Report Cards](#11-report-cards)
12. [Finance](#12-finance)
13. [Payroll](#13-payroll)
14. [Accounting](#14-accounting)
15. [Library](#15-library)
16. [Transport](#16-transport)
17. [Inventory](#17-inventory)
18. [Health](#18-health)
19. [Welfare](#19-welfare)
20. [NGO Partners](#20-ngo-partners)
21. [Promotion](#21-promotion)
22. [Reports](#22-reports)
23. [Roles & Access Control](#23-roles--access-control)
24. [Audit Log](#24-audit-log)
25. [Daily & Weekly Routines](#25-daily--weekly-routines)

---

## 1. How the System Works

School MIS is a **web application** that runs on a small server (usually a Raspberry Pi) inside the school. Staff access it from any phone, tablet, or computer connected to the school's Wi-Fi — no app installation needed, just open a browser.

**Access it at:** `http://<server-ip>:8765`

**Key things to know:**
- All data is stored in a single file on the server. Back it up regularly.
- Everything is role-based — each staff member only sees the modules they are permitted to use.
- The Administrator sets up everything and creates accounts for all other staff.

---

## 2. First-Time Setup (Setup Wizard)

When you open the system for the very first time you will see the **Setup Wizard**. This runs only once.

### Step 1 — School Information
Fill in:
- **School Name** (required) — appears on all reports and report cards
- **School Type** — Primary, Secondary, Mixed, or Nursery
- **Address, Phone, Email** — used on printed documents

### Step 2 — Admin Account
Create the administrator login:
- **Full Name** — the admin's real name
- **Username** — used to log in (e.g. `admin` or `john.doe`)
- **Password** — minimum 8 characters. Write this down and keep it safe.

### Step 3 — Review & Finish
Check the details and click **Complete Setup**. You will be taken to the login page.

> **After logging in for the first time, go immediately to Settings to complete the configuration before adding any data.**

---

## 3. Settings — Configure Before Anything Else

Go to **Settings** from the left sidebar. You will see tabs at the top.

---

### 3.1 School Information

**Tab: School Info**

Update or correct:
- School name, address, phone, email, motto
- School type (Primary / Secondary / Mixed)

Click **Save Changes** when done.

---

### 3.2 Academic Years

**Tab: Academic Years**

An Academic Year defines the school calendar. You must have at least one academic year before you can create classes, record fees, or enter grades.

**To add an academic year:**
1. Click **Add Academic Year**
2. Enter the label (e.g. `2024/2025`)
3. Enter start date and end date
4. Click **Save**
5. Click the **Set Current** button next to the active year

> Only one academic year can be "current" at a time. Always set the current year before starting any term.

---

### 3.3 Subjects

**Tab: Subjects**

Subjects are what teachers teach and students are graded on. The system comes with 8 default subjects for a primary school:

| Subject | Code |
|---|---|
| Mathematics | MATH |
| English Language | ENG |
| Kiswahili | KSW |
| Science | SCI |
| Social Studies | SST |
| Religious Education | RE |
| Physical Education | PE |
| Arts & Craft | ART |

**To add a new subject:**
1. Click **Add Subject**
2. Enter: Name, Code (short abbreviation), Type (Compulsory / Elective / Optional), Grade Level (leave blank for all grades), Credit Hours
3. Click **Save**

**To deactivate a subject** the school no longer teaches, click the toggle button. Inactive subjects are hidden from dropdowns but not deleted.

> For a secondary school, add subjects like Physics, Chemistry, Biology, History, Geography, etc.

---

### 3.4 User Accounts & Roles

**Tab: Users**

Create an account for every staff member who needs to use the system.

**Available roles:**

| Role | What they can do |
|---|---|
| **Administrator** | Everything — full access to all modules |
| **Head Teacher** | All school operations, approve grades, manage users (except admin) |
| **Academic Officer** | Grades, attendance, exams, report cards, academic reports |
| **Class Teacher** | Attendance for their class, enter grades, homework, leave requests |
| **Subject Teacher** | Enter grades for their assigned subjects only |
| **Accountant** | Fee collection, billing, accounting, payroll |
| **Store Keeper** | Inventory stock management |
| **Librarian** | Library catalogue and book loans |
| **Nurse** | Health visit records |
| **Welfare Officer** | Student welfare classification and sponsorship |

**To create a user:**
1. Click **Add User**
2. Enter Full Name, Username, Password (min 8 characters), and Role
3. For Class Teacher or Subject Teacher, also select the linked Teacher record
4. Click **Save**

> Share the username and password with the staff member and ask them to change it on first login.

---

## 4. Classes

**Sidebar: People → Classes**

Classes are the groups students belong to. Set these up before adding students.

**To add a class:**
1. Click **Add Class**
2. Enter: Class Name (e.g. `Standard 1A`), Grade Level (1–13), Academic Year, Room (optional), Capacity
3. Click **Save**

**Assigning a class teacher:**
After creating the class, you can assign a teacher as the class teacher from the **Teachers** module (see Section 5).

> Create all classes for the current academic year before enrolling students.

---

## 5. Teachers

**Sidebar: People → Teachers**

The Teachers module manages teacher records (personal details, qualifications). It is separate from user accounts — a teacher record holds the person's details, while a user account is their login.

**To add a teacher:**
1. Click **Add Teacher**
2. Fill in: First Name, Last Name, Gender, Phone, Email, Qualification, Hire Date
3. Click **Save**

**Assigning subjects and classes:**
After creating the teacher record, link it to a user account in Settings (Teacher Accounts tab). From there, assignments (which subject in which class) are managed through **Roles & Access → Teacher Assignments**.

---

## 6. Students

**Sidebar: People → Students**

**To add a student:**
1. Click **Add Student**
2. Fill in: Admission Number (unique), First Name, Last Name, Gender, Date of Birth, Class, Parent Name, Parent Phone
3. Click **Save**

**Admission Number:** Use a consistent format, e.g. `2024/001`, `2024/002`. The system does not auto-generate this — you assign it.

**Editing a student:**
Click the pencil icon next to the student's name. You can update all details including class transfer.

**Deactivating a student:**
When a student leaves, click the toggle to mark them inactive. Their records are preserved.

> Add all students before the term starts. A student must be in the system before you can record attendance, fees, or grades for them.

---

## 7. Guardians

**Sidebar: People → Guardians**

Guardians are parents or next-of-kin linked to students. Adding them allows you to manage parent portal accounts later.

**To add a guardian:**
1. Click **Add Guardian**
2. Enter Name, Phone, Email, Relationship
3. Link to one or more students
4. Click **Save**

---

## 8. Enrollment

**Sidebar: Academics → Enrollment**

Enrollment tracks which students are formally enrolled in which class for the current academic year. After adding students and classes, enroll students here.

**To enroll a student:**
1. Click **New Enrollment**
2. Select Student, Class, and Academic Year
3. Set status to **Active**
4. Click **Save**

---

## 9. Attendance

**Sidebar: Academics → Attendance**

Attendance is marked per class per day.

**To mark attendance:**
1. Select the **Class** and **Date**
2. For each student, set status: **Present**, **Absent**, **Late**, or **Excused**
3. Add notes for absences if needed
4. Click **Save**

**Who can mark attendance:**
- Class Teachers — for their own class
- Academic Officers and Head Teachers — for any class

**Viewing attendance reports:**
Go to **Reports → Attendance** to see summaries by class, student, or date range.

> Mark attendance every morning. Consistent records are required for term reports.

---

## 10. Grades & Exams

**Sidebar: Academics → Grades**

The grades workflow has three steps: **Enter → Submit → Approve → Publish**

### Step 1 — Create an Exam
The Academic Officer or Head Teacher creates the exam first:
1. Go to **Grades → Exam Management**
2. Click **New Exam**
3. Enter: Name (e.g. `Term 1 Examination`), Academic Year, Term (1/2/3), Start Date, End Date
4. Click **Save**

### Step 2 — Enter Grades (Teachers)
1. Go to **Grades → Grade Entry**
2. Select the Exam, Class, and Subject
3. Enter the score for each student (out of the maximum score)
4. Click **Submit** when finished — grades are locked for editing

### Step 3 — Approve Grades (Academic Officer / Head Teacher)
1. Go to **Grades → Approvals**
2. Review submitted grades
3. Click **Approve** to confirm, or **Reject** with a comment to send back for correction

### Step 4 — Publish Grades
After approval, click **Publish** to make grades visible on report cards and to parents.

**Grade Change Requests:**
If a teacher needs to correct a locked grade, they submit a change request from **Grades → Change Requests**. The Academic Officer reviews and approves or rejects it.

---

## 11. Report Cards

**Sidebar: Academics → Report Cards**

Report cards are generated after grades are published.

**To generate report cards:**
1. Select the Exam and Class
2. Click **Generate Report Cards**
3. Review — class teachers can add comments
4. Click **Publish** to make report cards visible to parents (via parent portal)
5. Click **Download** to get PDF versions for printing

---

## 12. Finance

**Sidebar: Operations → Finance**

Finance covers fee structures, billing, and payments.

### 12.1 — Set Up Fee Structures
Before billing students, define what fees are charged.

1. Go to **Finance → Fee Structures**
2. Click **Add Fee Structure**
3. Select: Academic Year, Fee Type (e.g. Tuition, Exam Fee, Activity Fee), Amount, Term, Due Date
4. You can set different amounts per class if needed
5. Click **Save**

### 12.2 — Generate Bills
After setting up fee structures:
1. Click **Generate Bills**
2. Select Academic Year and Term
3. The system creates a bill for every active student
4. Each bill gets a unique **Control Number**

### 12.3 — Record Payments
When a student pays:
1. Search for the student
2. Click **Record Payment** on their bill
3. Enter: Amount Paid, Payment Method (Cash / Mobile Money / Bank Transfer / Cheque), Reference Number
4. Click **Save** — a receipt number is generated automatically

### 12.4 — Fee Waivers
For orphans, sponsored students, or staff children:
1. Find the student's bill
2. Click **Add Waiver**
3. Select Waiver Type: Orphan Exemption, Scholarship, Partial Discount, Staff Child, Other
4. Enter the discount percentage
5. Waivers require approval from the Head Teacher or Administrator

### 12.5 — Payment Reports
Go to **Finance → Reports** to see:
- Outstanding balances per student / class
- Collection summary for the term
- Payment history

---

## 13. Payroll

**Sidebar: Operations → Payroll**

Payroll manages monthly staff salaries.

**To run payroll:**
1. Go to **Payroll**
2. Click **New Payroll Run**
3. Select Month and Year
4. The system lists all active teachers/staff with their base salary
5. Adjust allowances or deductions as needed
6. Click **Process** to finalise
7. Click **Download** to get the payroll report for the bank

**Setting up salary structures:**
Before running payroll, set each teacher's basic salary in their teacher record.

---

## 14. Accounting

**Sidebar: Operations → Accounting**

Accounting tracks school expenses (purchases, utilities, supplies, etc.) and gives a financial overview.

**To record an expense:**
1. Click **Record Expense**
2. Select Category: Salaries, Utilities, Supplies, Maintenance, Transport, Welfare, Other
3. Enter Description, Amount, Date, and Receipt Reference
4. Click **Save**

**Reports:**
View income vs. expenses, expense breakdowns, and balance summaries under **Accounting → Reports**.

---

## 15. Library

**Sidebar: Academics → Library**

**To add books to the catalogue:**
1. Click **Add Book**
2. Enter: Title, Author, ISBN, Category (Textbook / Fiction / Reference / etc.), Shelf Location, Number of Copies
3. Click **Save**

**To issue a book (checkout):**
1. Search for the book
2. Click **Issue**
3. Select: Borrower Type (Student / Teacher), select the borrower, set Due Date
4. Click **Confirm**

**To return a book:**
1. Go to **Active Loans**
2. Find the loan and click **Return**
3. If the book is overdue, enter any fine amount

---

## 16. Transport

**Sidebar: Operations → Transport**

**To set up a route:**
1. Click **Add Route**
2. Enter: Route Name, Description, Vehicle Number, Driver Name, Driver Phone, Term Fares (Term 1/2/3)
3. Click **Save**

**To assign students to a route:**
1. Click on a route name
2. Click **Assign Students**
3. Select Class, then select the student(s) from that class
4. Select Academic Year and Term
5. Click **Assign**

Students assigned to a route appear in the route manifest that the driver can use.

---

## 17. Inventory

**Sidebar: Operations → Inventory**

Inventory tracks school supplies: uniforms, books, stationery, equipment.

**To add an item:**
1. Click **Add Item**
2. Enter: Name, Category, Unit (pcs / kg / litres), Unit Price, Reorder Level
3. Click **Save**

**To record incoming stock:**
1. Click on the item
2. Click **Stock In**
3. Enter quantity received and reference number (e.g. LPO or delivery note number)

**To issue items to students:**
1. Click **Issue**
2. Select Student and quantity
3. Click **Confirm**

**Reorder Alerts:**
Items below their reorder level are highlighted in red.

---

## 18. Health

**Sidebar: Welfare → Health**

Records student visits to the school nurse or health room.

**To record a health visit:**
1. Click **New Visit**
2. Select Student
3. Fill in: Date, Time, Symptoms, Diagnosis, Treatment, Action Taken (Treated / Referred / Sent Home / Rest)
4. Check **Parent Notified** if you contacted the parent
5. Click **Save**

**Reports:**
View visit frequency, common illnesses, and referral rates under Health Reports.

---

## 19. Welfare

**Sidebar: Welfare → Welfare**

Tracks the welfare status of vulnerable students: orphans, half-orphans, and sponsored students.

**To classify a student:**
1. Click **Add Welfare Record**
2. Select Student
3. Set Category: Orphan, Half-Orphan, Sponsored, Vulnerable
4. Add Sponsor Name and Organisation (if sponsored)
5. Set Support Type: Full Fees, Partial, Non-Financial
6. Click **Save**

**Verification:**
Welfare records must be verified by the Head Teacher or Welfare Officer before they take effect for fee waivers.

---

## 20. NGO Partners

**Sidebar: Welfare → NGO Partners**

Records organisations that support the school (sponsors, donors, partners).

**To add an NGO partner:**
1. Click **Add Partner**
2. Enter: Organisation Name, Contact Person, Phone, Email, Support Type
3. Link to sponsored students if applicable
4. Click **Save**

---

## 21. Promotion

**Sidebar: Welfare → Promotion**

At the end of the academic year, promote students to the next class, hold them back, or graduate them.

**To promote students:**
1. Select the Source Class (e.g. Standard 3A)
2. For each student, choose: **Promote** (moves to next class), **Hold Back** (repeats the year), or **Graduate** (leaves the school)
3. Select the Destination Class for promoted students
4. Click **Apply Promotions**

> Run promotions only after all grades are published and report cards are generated.

---

## 22. Reports

**Sidebar: System → Reports**

The Reports module brings together data from all modules in one place.

| Report | What it shows |
|---|---|
| **Academic** | Exam results, grade distributions, class performance ranking |
| **Attendance** | Attendance rates by student, class, or date range |
| **Finance** | Fee collection, outstanding balances, payment history |
| **Payroll** | Monthly payroll summaries |
| **Welfare** | Orphan and sponsored student lists |
| **Inventory** | Stock levels, issued items, reorder alerts |

**Exporting:** Most reports can be downloaded as PDF or Excel.

---

## 23. Roles & Access Control

**Sidebar: System → Roles & Access**

*Only the Administrator can access this module.*

This is where you fine-tune which roles can access which features. The system ships with sensible defaults, but you can customise permissions for any role.

**To view or edit a role's permissions:**
1. Click on the role name (e.g. Head Teacher)
2. Check/uncheck permissions
3. Click **Save**

**User Roles tab:**
Shows all users and their current role assignment. You can change a user's role here.

> Be careful when removing permissions from the Administrator role — you could lock yourself out.

---

## 24. Audit Log

**Sidebar: System → Audit Log**

*Accessible to Administrator and Head Teacher.*

Every significant action in the system is logged: who did it, what they did, and when. Use this to:
- Track changes to student or financial records
- Investigate discrepancies
- Monitor staff activity

You can filter by user, date range, or action type.

---

## 25. Daily & Weekly Routines

### Every Morning
1. **Attendance** — Class teachers mark attendance for their class
2. **Health** — Nurse records any visits

### Every Week
1. **Library** — Check for overdue books and send reminders
2. **Finance** — Record any payments received

### Every Term
1. **Exams** — Academic Officer creates the exam record
2. **Grades** — Teachers enter and submit grades
3. **Approvals** — Academic Officer/Head Teacher approves grades
4. **Report Cards** — Generate, add comments, publish
5. **Finance** — Generate bills for the next term, follow up on outstanding fees
6. **Payroll** — Run monthly payroll for each month of the term
7. **Inventory** — Check stock levels and reorder if needed

### End of Year
1. Ensure all grades are approved and published
2. Generate final report cards
3. Run **Promotion** for all classes
4. Add a new **Academic Year** in Settings
5. Create new classes for the next year
6. Back up the database: `cp /opt/school_mis/school_mis.db /backup/school_mis_YYYY.db`

---

## Quick Reference — First Week Checklist

Work through these in order:

- [ ] Run Setup Wizard (login page appears on first open)
- [ ] Settings → School Info — verify school name and details
- [ ] Settings → Academic Years — add current year, set as current
- [ ] Settings → Subjects — add or remove subjects as needed
- [ ] Settings → Users — create accounts for all staff
- [ ] Classes — add all classes for the current year
- [ ] Teachers — add all teacher records
- [ ] Students — enrol all students
- [ ] Guardians — add parent/guardian details
- [ ] Finance → Fee Structures — set up fees for the year
- [ ] Finance → Generate Bills — create bills for Term 1
- [ ] Transport — add routes and assign students
- [ ] Library — add book catalogue
- [ ] Inventory — set up stock items with opening quantities

Once these are done, the system is ready for daily use.

---

*For technical issues (server not starting, password reset, updates), refer to DEPLOY.md.*
