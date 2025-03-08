assessments	CREATE TABLE assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    assessment_type TEXT NOT NULL,
    description TEXT,
    lesson_id INTEGER,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
block_records	CREATE TABLE block_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_record_id INTEGER NOT NULL,
    block_id INTEGER NOT NULL,
    student_speech_notes TEXT,
    teacher_notes TEXT,
    student_questions TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME,
    FOREIGN KEY (lesson_record_id) REFERENCES lesson_records(id),
    FOREIGN KEY (block_id) REFERENCES blocks(id)
)
blocks	CREATE TABLE blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    activity_type TEXT,
    content TEXT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
courses	CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration TEXT,
    focus TEXT,
    themes TEXT,
    grammar_overview TEXT,
    vocabulary_overview TEXT
)
enrolled_students	CREATE TABLE enrolled_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    enrollment_date DATE NOT NULL,
    course_id INTEGER NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id)
)
grammar_rules	CREATE TABLE grammar_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    rule TEXT NOT NULL,
    example TEXT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
lesson_records	CREATE TABLE lesson_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    completion_date DATE,
    score INTEGER,
    feedback TEXT,
    FOREIGN KEY (student_id) REFERENCES enrolled_students(id),
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
lessons	CREATE TABLE lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL,
    lesson_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    context TEXT,
    grammar_focus TEXT,
    vocabulary_focus TEXT,
    FOREIGN KEY (unit_id) REFERENCES units(id)
)
resources	CREATE TABLE resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    resource_type TEXT NOT NULL,
    description TEXT,
    url_or_path TEXT NOT NULL,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
sqlite_sequence	CREATE TABLE sqlite_sequence(name,seq)
units	CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    unit_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
)
vocabulary	CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    word_or_phrase TEXT NOT NULL,
    definition TEXT,
    example_usage TEXT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
)
