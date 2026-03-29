"""
utils.py — 工具函数
JSON 清洗、默认值兜底、sample 加载、fallback 数据
"""

import copy
import json
import os
import re


def clean_json_response(text: str) -> dict:
    """从 LLM 返回的文本中提取 JSON，处理 markdown code block、<think> 标签等情况"""
    if not text or not text.strip():
        return {}

    text = text.strip()

    # 去掉 <think>...</think> 推理标签（部分模型如 Minimax M2.5 会输出）
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    # 去掉 markdown code block 包裹
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # 尝试找到 JSON 对象
    # 有时模型会在 JSON 前后加多余文字
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 最后尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def safe_get(data: dict, key: str, default=None):
    """安全取值，避免 KeyError"""
    if not isinstance(data, dict):
        return default
    return data.get(key, default) or default


def ensure_action_card_structure(card: dict) -> dict:
    """确保 Action Card 有完整的 5 个模块结构，缺失字段用默认值兜底"""
    defaults = {
        "what_is_this_task": "Task description not available.",
        "key_requirements": ["No specific requirements extracted."],
        "deliverables_and_deadlines": ["Deadline not clearly stated"],
        "team_actions": {
            "first": "Read through the full brief together and identify key deliverables.",
            "next": "Divide responsibilities and begin working on core tasks.",
            "final": "Review all deliverables, check requirements, and submit on time.",
        },
        "risks_and_missing_info": ["Please review the original text for complete details."],
    }

    result = {}
    for key, default_val in defaults.items():
        val = safe_get(card, key, default_val)
        # 确保列表类型字段不为空
        if isinstance(default_val, list) and (not val or not isinstance(val, list)):
            val = default_val
        # 确保 team_actions 结构完整
        if key == "team_actions":
            if not isinstance(val, dict):
                val = default_val
            else:
                for sub_key in ["first", "next", "final"]:
                    if sub_key not in val or not val[sub_key]:
                        val[sub_key] = default_val[sub_key]
        result[key] = val

    return result


def ensure_structured_data(data: dict) -> dict:
    """确保 structured extraction 数据结构完整"""
    defaults = {
        "task_type": "notice",
        "objective": "Not specified",
        "key_requirements": [],
        "deliverables": [],
        "deadlines": ["Deadline not clearly stated"],
        "constraints": [],
        "important_notes": [],
        "missing_info": [],
    }

    result = {}
    for key, default_val in defaults.items():
        val = safe_get(data, key, default_val)
        if isinstance(default_val, list) and (not val or not isinstance(val, list)):
            val = default_val
        result[key] = val

    return result


def load_sample(name: str) -> str:
    """加载 demo 样本文件"""
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
    file_map = {
        "Assignment Brief": "demo_assignment.txt",
        "Hackathon Notice": "demo_hackathon.txt",
        "Event Instruction": "demo_event.txt",
        "Exam Notice": "demo_exam.txt",
        "Scholarship Application": "demo_application.txt",
        "Campus Notice": "demo_notice.txt",
    }
    filename = file_map.get(name, "")
    if not filename:
        return ""
    filepath = os.path.join(samples_dir, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[Sample file not found: {filename}]"


def get_sample_names() -> list:
    """返回所有可用 sample 名称"""
    return ["Assignment Brief", "Hackathon Notice", "Event Instruction", "Exam Notice", "Scholarship Application", "Campus Notice"]


# ============================================================
# DEMO_MODE fallback 数据
# 当 DEMO_MODE=true 或 API 不可用时，使用这些预设结果
# ============================================================

DEMO_RESULTS = {
    "Assignment Brief": {
        "task_type": "assignment",
        "structured_data": {
            "task_type": "assignment",
            "objective": "Design and implement a software application addressing a real-world problem as a team of 3-4, following agile practices. Worth 40% of module mark.",
            "key_requirements": [
                "Choose a problem domain: campus life, sustainability, or education",
                "Develop a working prototype with any language/framework",
                "Must include at least one external API integration",
                "Write a technical report (max 3000 words)",
                "Prepare 10-minute group presentation + 5-minute Q&A",
                "All code on shared GitHub with clear commit history",
            ],
            "deliverables": [
                "Technical Report (via Moodle)",
                "Group Presentation (in-class)",
                "GitHub Repository Link (via Moodle)",
                "Peer Assessment Form (individual)",
            ],
            "deadlines": [
                "Technical Report & GitHub Link: 23:59, Friday 17 April 2026",
                "Presentation: Week 11 (28 April – 2 May 2026), exact slot TBA",
                "Peer Assessment: 23:59, Sunday 4 May 2026",
            ],
            "constraints": [
                "Max 3000 words for report",
                "Must use agile development practices",
                "AI tool usage must be declared and documented",
                "Late penalty: max 40% within 5 days, 0% after",
            ],
            "important_notes": [
                "Each member must write their own individual contribution section",
                "Undeclared AI use may be treated as academic misconduct",
                "Office hours: Wednesday 14:00-16:00, Room SA302",
            ],
            "missing_info": [
                "Exact presentation time slot not announced yet",
                "No specific rubric details for each marking criterion",
                "Team formation process not specified",
                "Report formatting requirements not specified",
            ],
        },
        "action_card": {
            "what_is_this_task": "A group software engineering project (40% of COMP2043) where your team of 3-4 builds a working prototype addressing campus life, sustainability, or education, with a report and presentation.",
            "key_requirements": [
                "Build a working prototype with at least one external API integration",
                "Follow agile development practices (sprints, stand-ups, retrospectives)",
                "Write a 3000-word technical report with individual contribution sections",
                "Prepare a 10-minute presentation with 5-minute Q&A",
                "Host all code on GitHub with clear individual commit history",
                "Declare and document any AI tool usage",
            ],
            "deliverables_and_deadlines": [
                "Technical Report + GitHub Link — 23:59, Friday 17 April 2026 (via Moodle)",
                "Group Presentation — Week 11 (28 April – 2 May 2026), exact slot TBA",
                "Peer Assessment Form — 23:59, Sunday 4 May 2026 (individual, via Moodle)",
            ],
            "team_actions": {
                "first": "Meet as a team this week: pick a problem domain, agree on tech stack, set up GitHub repo, and create a sprint plan for the first two weeks.",
                "next": "Divide work — one person leads backend/API integration, one leads frontend/UX, one leads report drafting. Run weekly check-ins and commit code regularly to show individual contributions.",
                "final": "Freeze features one week before deadline. Polish the report, rehearse the 10-minute presentation, cross-review each other's individual contribution sections, and submit all materials before 17 April.",
            },
            "risks_and_missing_info": [
                "Exact presentation slot TBA — watch for announcements in Week 10",
                "No detailed rubric for each marking criterion — ask on module forum",
                "Team formation method not specified — clarify with module convenor",
                "Report format (template, font, spacing) not specified",
                "Late submission penalty is harsh: max 40% within 5 days, 0% after",
            ],
        },
    },
    "Hackathon Notice": {
        "task_type": "competition",
        "structured_data": {
            "task_type": "competition",
            "objective": "Build an AI-powered tool in 30 hours that improves campus life, promotes sustainability, or enhances education.",
            "key_requirements": [
                "Team of 3-5 members, cross-faculty encouraged",
                "At least one non-CS member required",
                "All coding during the 30-hour window",
                "Must use at least one AI/ML component",
                "Core logic must be original",
            ],
            "deliverables": [
                "GitHub repository with README",
                "3-slide pitch deck (problem, solution, demo)",
                "Live demo or recorded demo video (max 2 min)",
            ],
            "deadlines": [
                "All submissions via hackathon portal by 12:00, 29 March 2026",
                "Code freeze at 12:00, 29 March 2026",
                "Presentations start at 13:00, 29 March 2026",
            ],
            "constraints": [
                "Pre-existing libraries allowed, but core logic must be original",
                "5-min pitch + 3-min Q&A per team",
                "Must include: project description, tech stack, how to run, team members in README",
            ],
            "important_notes": [
                "API credits for MiniMax provided at check-in",
                "Registration deadline was 20 March 2026",
                "Judging weighs Product Maturity (20%) and AI Depth (20%) heavily",
            ],
            "missing_info": [
                "Specific API credit amounts not stated",
                "Whether teams can be formed on-site",
                "Food/accommodation details beyond breakfast and dinner",
                "Whether remote participation is allowed",
            ],
        },
        "action_card": {
            "what_is_this_task": "A 30-hour AI hackathon at UNNC where teams of 3-5 build an AI tool under the theme 'AI for Good — Campus Edition', competing for prizes up to ¥5000.",
            "key_requirements": [
                "Team of 3-5 with at least one non-CS member",
                "Must include at least one AI/ML component (API calls count)",
                "All core coding done within the 30-hour window",
                "Submit GitHub repo, 3-slide pitch deck, and demo video",
                "5-minute pitch + 3-minute Q&A presentation",
            ],
            "deliverables_and_deadlines": [
                "GitHub repo + pitch deck + demo video — 12:00, 29 March 2026 (hackathon portal)",
                "Code freeze — 12:00, 29 March 2026",
                "Presentation — 13:00, 29 March 2026 (5 min pitch + 3 min Q&A)",
            ],
            "team_actions": {
                "first": "Arrive at 09:00 on 28 March, finalize your idea during opening ceremony, set up GitHub repo and dev environment by 10:00 when hacking begins.",
                "next": "Build the MVP — one person on AI/backend, one on frontend/demo, one on pitch deck and documentation. Hit a working demo by midnight, then iterate.",
                "final": "Before 12:00 on 29 March: freeze code, record demo video (max 2 min), finalize README with project description and run instructions, submit everything via portal, and rehearse 5-min pitch.",
            },
            "risks_and_missing_info": [
                "Registration deadline was 20 March — confirm your team is registered",
                "Specific API credit amounts not stated — plan for potential limits",
                "Whether remote participation is possible — not mentioned",
                "Judging weights Product Maturity (20%) and AI Depth (20%) heavily — prioritize a polished working demo over feature count",
                "No mention of whether teams can be formed on-site",
            ],
        },
    },
    "Event Instruction": {
        "task_type": "event",
        "structured_data": {
            "task_type": "event",
            "objective": "Recruit booth coordinators and event volunteers for the UNNC International Cultural Festival on 12 April 2026.",
            "key_requirements": [
                "Booth Coordinators: manage a cultural booth with 3-5 team members",
                "Event Volunteers: available for full day (09:00-19:00)",
                "Booth coordinators must attend one mandatory training session",
                "All volunteers must attend the briefing session",
                "Booth coordinators must submit a booth proposal with application",
            ],
            "deliverables": [
                "Application form (via forms.unnc.edu.cn/culturalfest2026)",
                "Booth proposal for coordinators (theme, activities, budget estimate)",
            ],
            "deadlines": [
                "Application deadline: 23:59, Sunday 30 March 2026",
                "Results announced by: Wednesday 2 April 2026",
                "Training sessions: 2 April 18:00-19:30 OR 5 April 14:00-15:30",
                "Volunteer briefing: 10 April 18:00-19:00",
                "Event day: 12 April 2026, 10:00-18:00",
            ],
            "constraints": [
                "Booth setup begins at 08:00 on event day",
                "Volunteers must be available full day 09:00-19:00",
                "Absence from briefing without notice may result in removal",
                "Rain contingency: moved to Sports Hall with limited capacity",
            ],
            "important_notes": [
                "Priority given to students who haven't participated before",
                "CCA hours: 5 for volunteers, 8 for booth coordinators",
                "Free t-shirt, lunch, and certificate provided",
            ],
            "missing_info": [
                "Volunteer briefing location TBA",
                "Booth budget limits not specified",
                "Selection criteria for applications not detailed",
                "Whether you can apply for both coordinator and volunteer roles",
            ],
        },
        "action_card": {
            "what_is_this_task": "A call for booth coordinators (20 spots) and event volunteers (50 spots) for the UNNC International Cultural Festival on 12 April 2026, with applications due 30 March.",
            "key_requirements": [
                "Choose a role: Booth Coordinator (manage a cultural booth, 3-5 per team) or Event Volunteer (registration, logistics, photography, etc.)",
                "Booth coordinators must submit a booth proposal (theme, activities, budget) with application",
                "All volunteers must attend the mandatory briefing on 10 April",
                "Booth coordinators must attend one of two training sessions",
                "Full-day commitment required on event day",
            ],
            "deliverables_and_deadlines": [
                "Application form — 23:59, Sunday 30 March 2026",
                "Booth proposal (coordinators only) — with application",
                "Attend training (coordinators) — 2 April 2026 or 5 April 2026",
                "Attend briefing (volunteers) — 10 April 2026, 18:00-19:00, location TBA",
                "Event day — 12 April 2026 (setup from 08:00, event 10:00-18:00)",
            ],
            "team_actions": {
                "first": "Decide as a team: coordinator or volunteer? If coordinator, brainstorm a booth theme and draft a proposal (theme, activities, budget estimate) this week.",
                "next": "Submit the application form before 30 March 23:59. If applying as booth coordinators, attach the booth proposal. Register for a training session (2 April or 5 April).",
                "final": "After results (by 2 April): attend your assigned training/briefing, prepare booth materials or confirm volunteer role, and be ready for setup at 08:00 on 12 April.",
            },
            "risks_and_missing_info": [
                "Volunteer briefing location is TBA — watch for announcements",
                "Booth budget limits not specified — ask the committee before spending",
                "Selection criteria not detailed — priority to first-time participants",
                "Unclear whether you can apply for both coordinator and volunteer",
                "Rain plan moves event to Sports Hall — some booths may be consolidated",
            ],
        },
    },
    "Exam Notice": {
        "task_type": "exam",
        "structured_data": {
            "task_type": "exam",
            "objective": "Mid-term examination for COMP2043 Software Engineering, a 2-hour closed-book written exam covering Weeks 1-6 content.",
            "key_requirements": [
                "Bring student ID card — mandatory for entry",
                "Arrive at least 15 minutes early; doors close at 14:10",
                "Black or blue pens only; no pencil for final answers",
                "No electronic devices, phones, or smartwatches",
            ],
            "deliverables": [
                "Section A: 20 MCQs (40 marks)",
                "Section B: 3 short-answer questions (30 marks)",
                "Section C: 1 case-study question out of 2 (30 marks)",
            ],
            "deadlines": [
                "Exam date: Wednesday 16 April 2026, 14:00-16:00",
                "Revision lecture: Monday 14 April 2026, 10:00-12:00",
                "Reasonable adjustments confirmation: Friday 11 April 2026",
            ],
            "constraints": [
                "Closed-book exam",
                "Simple non-programmable calculator permitted for Section B Q3 only",
                "Cannot leave in last 15 minutes; can leave after first 45 minutes",
                "Assigned seating — check noticeboard on exam day",
            ],
            "important_notes": [
                "Past papers (2024, 2025) available on Moodle",
                "Office hours for queries: Dr. Zhang, Wed 9 April, 14:00-16:00, SA302",
                "Cheating results in zero marks and referral to Academic Conduct Committee",
            ],
            "missing_info": [
                "Exact mark weighting of mid-term in overall module grade not stated",
                "Whether formula sheets or reference materials are provided",
                "Seating arrangement details not available until exam day",
            ],
        },
        "action_card": {
            "what_is_this_task": "A 2-hour closed-book mid-term exam for COMP2043 Software Engineering on 16 April 2026, covering SDLC, UML, design patterns, testing, and Agile methodology.",
            "key_requirements": [
                "Bring student ID card and black/blue pens",
                "Arrive by 13:45 — doors close at 14:10, no late entry",
                "No electronics allowed; simple calculator only for Section B Q3",
                "Know the 3-section format: MCQ (40), short-answer (30), case-study (30)",
            ],
            "deliverables_and_deadlines": [
                "Confirm reasonable adjustments — Friday 11 April 2026",
                "Attend revision lecture — Monday 14 April 2026, 10:00-12:00, SA-LT1",
                "Mid-term exam — Wednesday 16 April 2026, 14:00-16:00, PMB-G01",
            ],
            "team_actions": {
                "first": "Download past papers (2024, 2025) from Moodle and review the topic list: SDLC, requirements engineering, UML diagrams, design patterns, testing, Agile/Scrum, and Git.",
                "next": "Create a revision plan covering each topic area. Practice drawing UML diagrams by hand (class, sequence, activity). Review design pattern code examples. Do timed practice with past papers.",
                "final": "Attend the revision lecture on 14 April. Do a full mock exam under timed conditions. Prepare pens and ID card the night before. Check the seating noticeboard before entering PMB-G01.",
            },
            "risks_and_missing_info": [
                "Mid-term weight in overall grade not stated — check module handbook",
                "No formula sheets or reference materials confirmed — assume none",
                "Seating assignment only available on exam day — arrive early to find your seat",
                "Late entry after 14:10 is strictly not allowed",
                "Academic misconduct policy is strict — zero marks and committee referral",
            ],
        },
    },
    "Scholarship Application": {
        "task_type": "application",
        "structured_data": {
            "task_type": "application",
            "objective": "Apply for the UNNC Global Engagement Scholarship 2026-2027, offering full tuition waiver, monthly allowance, and flight ticket.",
            "key_requirements": [
                "Full-time Year 2 or Year 3 undergraduate at UNNC",
                "Cumulative GPA of 3.5/4.0 or above",
                "Active in at least 2 cross-cultural/community activities this year",
                "No academic misconduct or disciplinary record",
                "Not receiving other full scholarships for the same period",
            ],
            "deliverables": [
                "Completed application form",
                "Personal statement (800-1000 words)",
                "Academic transcript (unofficial accepted)",
                "Two recommendation letters",
                "Evidence of cross-cultural activities",
                "CV/Resume (max 2 pages)",
            ],
            "deadlines": [
                "Application opens: Monday 31 March 2026",
                "Application deadline: 23:59, Sunday 20 April 2026",
                "Shortlist notification: Wednesday 30 April 2026",
                "Interviews: 5-9 May 2026",
                "Results announced: Friday 23 May 2026",
            ],
            "constraints": [
                "Personal statement must be 800-1000 words",
                "CV must not exceed 2 pages",
                "Incomplete applications will not be considered",
                "Late submissions not accepted under any circumstances",
            ],
            "important_notes": [
                "Scholarship value: ~¥100,000 tuition + ¥1,500/month + flight up to ¥8,000",
                "Interview is 15 minutes, conducted in English",
                "Selection: academics 40%, personal statement 25%, activities 20%, interview 15%",
            ],
            "missing_info": [
                "Number of scholarships available not stated",
                "Whether the scholarship is renewable for subsequent years",
                "Specific format requirements for recommendation letters",
                "Whether digital/scanned signatures on recommendation letters are accepted",
            ],
        },
        "action_card": {
            "what_is_this_task": "A competitive scholarship application for the UNNC Global Engagement Scholarship, worth ~¥100,000 tuition waiver plus monthly stipend. Application deadline is 20 April 2026.",
            "key_requirements": [
                "GPA 3.5+ and Year 2 or 3 undergraduate at UNNC",
                "At least 2 cross-cultural/community activities this academic year",
                "Submit: application form, personal statement, transcript, 2 recommendation letters, activity evidence, CV",
                "Personal statement 800-1000 words; CV max 2 pages",
                "No other full scholarships held simultaneously",
            ],
            "deliverables_and_deadlines": [
                "Request recommendation letters — start immediately (allow 2+ weeks)",
                "Complete application form + all documents — 23:59, Sunday 20 April 2026",
                "Interview (if shortlisted) — 5-9 May 2026",
                "Results — Friday 23 May 2026",
            ],
            "team_actions": {
                "first": "Check eligibility: verify your GPA meets 3.5 threshold, list your cross-cultural activities, and identify two recommenders (one academic, one activity advisor). Request recommendation letters this week.",
                "next": "Draft your personal statement (800-1000 words) covering cross-cultural experiences, scholarship goals, and community contribution plan. Gather activity evidence and update your CV to 2 pages max.",
                "final": "Proofread everything, confirm recommendation letters are submitted, upload all documents to the portal before 20 April 23:59. If shortlisted, prepare for a 15-minute English interview focusing on your experiences and plans.",
            },
            "risks_and_missing_info": [
                "Number of scholarships available is not stated — likely very competitive",
                "Recommendation letters need lead time — request immediately",
                "Renewability not mentioned — may be one-year only",
                "Late/incomplete submissions explicitly rejected — no exceptions",
                "Interview weighs 15% — prepare even though it seems minor",
            ],
        },
    },
    "Campus Notice": {
        "task_type": "notice",
        "structured_data": {
            "task_type": "notice",
            "objective": "Multiple changes to Semester 2 teaching arrangements effective 7 April 2026: room reassignments, new attendance system, extended library hours, and module evaluation survey.",
            "key_requirements": [
                "Check updated timetable on UNNC Portal after 4 April",
                "Ensure student ID card works with new door readers before 7 April",
                "Complete Module Evaluation Survey between 7-20 April",
                "Note new Library hours: 07:00-23:30 Mon-Fri from 7 April",
            ],
            "deliverables": [
                "Module Evaluation Survey completion (7-20 April)",
            ],
            "deadlines": [
                "Updated timetables published: Friday 4 April 2026",
                "Changes effective: Monday 7 April 2026",
                "Module Evaluation Survey closes: Sunday 20 April 2026",
            ],
            "constraints": [
                "3+ unexplained absences → formal warning letter",
                "5+ unexplained absences → may be debarred from final exam",
                "Old paper sign-in sheets no longer accepted",
            ],
            "important_notes": [
                "TB3 rooms reassigned: TB3-101→PMB-LT2, TB3-201/202→SEB-305/306, TB3-Lab→Library Floor 4",
                "New digital attendance: scan student ID at door reader",
                "If card reader malfunctions, report to module convenor — do not leave",
            ],
            "missing_info": [
                "Whether TB3 renovation affects any other facilities",
                "How to resolve issues if student ID card doesn't work with new readers",
                "Whether extended library hours are permanent or temporary",
            ],
        },
        "action_card": {
            "what_is_this_task": "A campus-wide notice about 4 changes effective 7 April 2026: classroom relocations due to TB3 renovation, a new digital attendance system, extended library hours, and the module evaluation survey.",
            "key_requirements": [
                "Check your updated timetable on UNNC Portal after 4 April for room changes",
                "Test your student ID card at the Library entrance before 7 April",
                "Understand the new attendance rules: scan ID at door, 3+ absences = warning, 5+ = exam debarment",
                "Complete Module Evaluation Survey on UNNC Portal by 20 April",
            ],
            "deliverables_and_deadlines": [
                "Check new timetable — after Friday 4 April 2026",
                "Test student ID with door readers — before Monday 7 April 2026",
                "Changes take effect — Monday 7 April 2026",
                "Module Evaluation Survey — 7-20 April 2026",
            ],
            "team_actions": {
                "first": "Read this notice carefully and understand all 4 changes. Check which of your classes were in TB3 and note the new room locations.",
                "next": "After 4 April, log into UNNC Portal and verify your personal timetable. Test your student ID card at the Library entrance to ensure it works with the new door readers.",
                "final": "From 7 April, go to the correct new rooms. Remember to scan your ID card at every class. Complete the Module Evaluation Survey before 20 April.",
            },
            "risks_and_missing_info": [
                "If your ID card doesn't work with new readers, resolution process is unclear — visit Academic Services at AB-128",
                "Whether TB3 renovation affects other facilities not mentioned",
                "Extended library hours may be temporary — not confirmed",
                "Missing a scan counts as unexplained absence even if you attended — always scan",
                "Card reader malfunction: report to convenor immediately, do NOT leave class",
            ],
        },
    },
}


# ============================================================
# Naive Summary 对比数据 — 展示"普通 AI 总结"和我们 Action Card 的差异
# ============================================================
NAIVE_SUMMARIES = {
    "Assignment Brief": (
        "This is a group coursework for COMP2043 Software Engineering worth 40% of the module mark. "
        "Students work in teams of 3-4 to design and implement a software application addressing "
        "campus life, sustainability, or education. They need to submit a technical report, give a "
        "presentation, and maintain a GitHub repository. The report deadline is April 17, 2026."
    ),
    "Hackathon Notice": (
        "The UNNC 30-Hour AI Hackathon 2026 is scheduled for March 28-29 at Teaching Building 1. "
        "Teams of 3-5 members will build AI tools under the theme 'AI for Good — Campus Edition'. "
        "Submissions include a GitHub repo, pitch deck, and demo video, all due by 12:00 on March 29. "
        "Prizes range from ¥1000 to ¥5000."
    ),
    "Event Instruction": (
        "The UNNC International Cultural Festival will be held on April 12, 2026. The organizers "
        "are recruiting 20 booth coordinators and 50 event volunteers. Applications are due by "
        "March 30, 2026. Booth coordinators need to submit a proposal and attend training, while "
        "volunteers must attend a briefing session."
    ),
    "Exam Notice": (
        "The COMP2043 Software Engineering mid-term exam will be held on April 16, 2026, from "
        "14:00 to 16:00 in PMB-G01. It is a 2-hour closed-book written exam with three sections: "
        "multiple choice, short answers, and a case study. Students must bring their ID card and "
        "arrive 15 minutes early."
    ),
    "Scholarship Application": (
        "The UNNC Global Engagement Scholarship for 2026-2027 offers a full tuition waiver and "
        "monthly allowance to Year 2 and Year 3 students with a GPA of 3.5 or above. Applicants "
        "need to submit a personal statement, transcript, two recommendation letters, and evidence "
        "of cross-cultural activities by April 20, 2026."
    ),
    "Campus Notice": (
        "Several changes to Semester 2 teaching arrangements at UNNC take effect on April 7, 2026. "
        "Classrooms in Teaching Building 3 are being relocated due to renovation. A new digital "
        "attendance system requires students to scan ID cards. The library will extend its weekday "
        "hours, and the module evaluation survey runs from April 7-20."
    ),
}


def get_demo_result(sample_name: str = "") -> dict:
    """获取 demo fallback 结果"""
    if sample_name in DEMO_RESULTS:
        result = copy.deepcopy(DEMO_RESULTS[sample_name])
        result["naive_summary"] = NAIVE_SUMMARIES.get(sample_name, "")
        return result

    result = copy.deepcopy(DEMO_RESULTS["Assignment Brief"])
    result["naive_summary"] = NAIVE_SUMMARIES.get("Assignment Brief", "")
    return result


def guess_demo_result(text: str) -> dict:
    """根据输入文本的关键词，选择最匹配的 demo 数据。
    在 DEMO_MODE 下处理自定义文本时使用，避免永远返回 Assignment Brief。"""
    text_lower = text.lower()

    # keyword → sample name mapping (order = priority)
    _KEYWORD_MAP = [
        (["exam", "mid-term", "midterm", "quiz", "test", "考试", "期中", "期末"], "Exam Notice"),
        (["scholarship", "funding", "award", "奖学金", "申请", "eligibility"], "Scholarship Application"),
        (["hackathon", "competition", "contest", "比赛", "challenge", "黑客松"], "Hackathon Notice"),
        (["event", "festival", "volunteer", "活动", "志愿", "cultural"], "Event Instruction"),
        (["notice", "announcement", "policy", "timetable", "通知", "公告", "安排"], "Campus Notice"),
        (["assignment", "coursework", "project", "report", "submit", "作业", "提交", "deadline"], "Assignment Brief"),
    ]

    for keywords, sample_name in _KEYWORD_MAP:
        if any(kw in text_lower for kw in keywords):
            result = copy.deepcopy(DEMO_RESULTS[sample_name])
            result["naive_summary"] = NAIVE_SUMMARIES.get(sample_name, "")
            return result

    # Fallback to Assignment Brief if no keywords match
    result = copy.deepcopy(DEMO_RESULTS["Assignment Brief"])
    result["naive_summary"] = NAIVE_SUMMARIES.get("Assignment Brief", "")
    return result
