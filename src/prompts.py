"""
prompts.py — 所有 AI prompt 模板
CampusBrief 的三步 workflow: Classify → Extract → Plan
每一步使用独立的 prompt，确保 AI 深度可解释

另含一个 naive summary prompt，用于对比展示
"""

# ============================================================
# Step 1: Task Classification
# 识别文本类型，为后续提取提供上下文
# 分类结果会直接影响 Step 2 的提取策略
# ============================================================
CLASSIFICATION_PROMPT = """You are a campus document classifier. Your job is to identify the type of campus-related document. The text may be in English, Chinese, or a mix of both — classify based on content regardless of language.

Classify the following text into exactly ONE of these categories:
- assignment (coursework, homework, group project, capstone, lab report, research proposal — anything students must complete and submit)
- competition (hackathon, contest, challenge, debate tournament)
- event (festival, workshop, seminar, orientation, volunteer call — gatherings to attend or help with)
- exam (mid-term, final exam, quiz, oral exam, viva, test — anything students must prepare for and sit)
- application (scholarship, internship, exchange program, job posting, funding — anything requiring an application)
- notice (policy change, enrollment, timetable update, campus alert, administrative announcement — informational documents)

Respond with ONLY a JSON object in this exact format:
{{"task_type": "<category>", "confidence": "<high/medium/low>"}}

Do NOT add any explanation. Only output the JSON.

TEXT:
{text}"""

# ============================================================
# Step 2: Structured Extraction
# 从原文中提取关键结构化字段
# 提取策略根据 task_type 自适应
# ============================================================
EXTRACTION_PROMPT = """You are a structured information extractor for campus documents. The document has been classified as: {task_type}. The text may be in English, Chinese, or bilingual — always output in English regardless of input language.

Extract the following fields from the text. Be precise and factual — only extract what is explicitly stated. If a field is not mentioned, use an empty list or "Not specified".

TYPE-SPECIFIC FOCUS:
- assignment: focus on deliverables, grading criteria, submission format, word count, group/individual requirements
- competition: focus on rules, team size, judging criteria, registration deadline, phases/rounds
- event: focus on date/time/venue, registration, what to prepare/bring, roles available
- exam: focus on exam date/time/venue, topics covered, allowed materials (open-book? calculator?), duration, format (essay/MCQ/oral)
- application: focus on eligibility criteria, required documents, application method, selection process, benefit/reward
- notice: focus on what changed, who is affected, what action is required, effective date

Respond with ONLY a JSON object in this exact format:
{{
  "task_type": "{task_type}",
  "objective": "<1-2 sentence summary of the core objective>",
  "key_requirements": ["<requirement 1>", "<requirement 2>", ...],
  "deliverables": ["<deliverable 1>", "<deliverable 2>", ...],
  "deadlines": ["<deadline 1 with date>", "<deadline 2 with date>", ...],
  "constraints": ["<constraint 1>", "<constraint 2>", ...],
  "important_notes": ["<note 1>", "<note 2>", ...],
  "missing_info": ["<info not clearly stated 1>", "<info not clearly stated 2>", ...]
}}

IMPORTANT:
- Do NOT invent information not in the original text.
- If no deadlines are found, set deadlines to ["Deadline not clearly stated"].
- missing_info should list things a student would need to know but the text does not clearly specify.

TEXT:
{text}"""

# ============================================================
# Step 3: Action Planning
# 基于结构化数据生成可执行的 Action Card
# ============================================================
ACTION_CARD_PROMPT = """You are an action planner for university students. Based on the structured extraction below, generate an Action Card that helps a team of 3 go from confusion to first action immediately. Always output in English.

STRUCTURED DATA:
{structured_data}

ORIGINAL TEXT:
{text}

Generate a JSON response in this EXACT format:
{{
  "what_is_this_task": "<1-2 sentences. Be specific and direct. Tell the student exactly what this is about.>",
  "key_requirements": ["<requirement 1>", "<requirement 2>", "<requirement 3>", ...],
  "deliverables_and_deadlines": ["<deliverable — deadline>", ...],
  "team_actions": {{
    "first": "<The very first thing the team/student should do. Be specific and actionable.>",
    "next": "<The second phase of work. Be specific about what to produce or prepare.>",
    "final": "<The final phase before the deadline. Include review/polish/submission steps.>"
  }},
  "risks_and_missing_info": ["<risk or missing info 1>", "<risk or missing info 2>", ...]
}}

RULES:
- what_is_this_task: Max 2 sentences. No filler words.
- key_requirements: Only the truly important ones. 3-6 bullets.
- deliverables_and_deadlines: Pair each deliverable/milestone with its deadline. If no deadline exists, write "Deadline not clearly stated".
- team_actions: Adapt steps to the document type:
  * assignment/competition: "First" = understand scope + divide work, "Next" = main production, "Final" = review + submit
  * exam: "First" = gather syllabus + past papers, "Next" = structured revision plan, "Final" = mock test + last review
  * application: "First" = check eligibility + gather documents, "Next" = draft application, "Final" = review + submit before deadline
  * event: "First" = register/sign up, "Next" = prepare what's needed, "Final" = confirm logistics on the day
  * notice: "First" = understand what changed, "Next" = identify required actions, "Final" = complete actions before effective date
- risks_and_missing_info: Things the original text didn't clarify, things easy to overlook, things students should NOT assume.

Do NOT invent dates or requirements not in the original text."""

# ============================================================
# Naive Summary Prompt — 用于和 Action Card 做对比展示
# 故意做成"普通 AI 总结"，让评委看到差异
# ============================================================
NAIVE_SUMMARY_PROMPT = """Summarize the following text in 3-4 sentences in English. Keep it concise and informative.

TEXT:
{text}"""
