import sqlite3
import csv

# Prompt user for student ID input
student_id = input("Enter the student ID: ")

# SQLite database file
db_file = "esl.db"

# Query to fetch student course, units, lessons, and block records
query = f"""
WITH student_courses AS (
    SELECT e.id AS student_id, c.id AS course_id, c.name AS course_name
    FROM enrolled_students e
    JOIN courses c ON e.course_id = c.id
    WHERE e.id = {student_id}
),
student_lessons AS (
    SELECT lr.lesson_id, lr.id AS lesson_record_id, u.course_id, u.id AS unit_id, u.title AS unit_title, 
           l.id AS lesson_id, l.title AS lesson_title, lr.feedback
    FROM lesson_records lr
    JOIN lessons l ON lr.lesson_id = l.id
    JOIN units u ON l.unit_id = u.id
    WHERE lr.student_id = {student_id}
)
SELECT 
    sc.course_id, 
    sc.course_name,
    sl.unit_id, 
    sl.unit_title, 
    sl.lesson_id, 
    sl.lesson_title, 
    sl.feedback, 
    b.id AS block_id, 
    b.block_number, 
    b.title AS block_title, 
    b.description AS block_description, 
    br.student_speech_notes, 
    br.teacher_notes, 
    br.student_questions, 
    br.created_at, 
    br.modified_at
FROM student_courses sc
JOIN student_lessons sl ON sc.course_id = sl.course_id
JOIN blocks b ON sl.lesson_id = b.lesson_id
LEFT JOIN block_records br ON br.block_id = b.id AND br.lesson_record_id = sl.lesson_record_id
WHERE sc.student_id = {student_id};
"""

try:
    # Connect to the database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Execute the query
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Check if data was retrieved
    if not rows:
        print(f"⚠️ No records found for student ID {student_id}")
        exit()

    # Organize data into a structured dictionary
    courses = {}
    for row in rows:
        (
            course_id,
            course_name,
            unit_id,
            unit_title,
            lesson_id,
            lesson_title,
            feedback,
            block_id,
            block_number,
            block_title,
            block_description,
            student_speech_notes,
            teacher_notes,
            student_questions,
            created_at,
            modified_at,
        ) = row

        if course_id not in courses:
            courses[course_id] = {"name": course_name, "units": {}}

        if unit_id not in courses[course_id]["units"]:
            courses[course_id]["units"][unit_id] = {"title": unit_title, "lessons": {}}

        if lesson_id not in courses[course_id]["units"][unit_id]["lessons"]:
            courses[course_id]["units"][unit_id]["lessons"][lesson_id] = {
                "title": lesson_title,
                "feedback": feedback,
                "blocks": [],
            }

        courses[course_id]["units"][unit_id]["lessons"][lesson_id]["blocks"].append(
            {
                "block_id": block_id,
                "block_number": block_number,
                "title": block_title,
                "description": block_description,
                "student_speech_notes": student_speech_notes,
                "teacher_notes": teacher_notes,
                "student_questions": student_questions,
                "created_at": created_at,
                "modified_at": modified_at,
            }
        )

    # Generate Markdown content
    md_file = f"student_{student_id}_records.md"
    with open(md_file, "w", encoding="utf-8") as md:
        md.write(f"# Student {student_id} Records\n\n")

        for course in courses.values():
            md.write(f"## Course: {course['name']}\n\n")

            for unit in course["units"].values():
                md.write(f"### Unit: {unit['title']}\n\n")

                for lesson in unit["lessons"].values():
                    md.write(f"#### Lesson: {lesson['title']}\n\n")
                    md.write(
                        f"**Feedback:** {lesson['feedback'] if lesson['feedback'] else 'No feedback available'}\n\n"
                    )

                    md.write("##### Blocks:\n")
                    for block in lesson["blocks"]:
                        md.write(
                            f"- **Block {block['block_number']}: {block['title']}**\n"
                        )
                        md.write(f"  - *Description:* {block['description']}\n")
                        md.write(
                            f"  - *Student Speech Notes:* {block['student_speech_notes'] if block['student_speech_notes'] else 'None'}\n"
                        )
                        md.write(
                            f"  - *Teacher Notes:* {block['teacher_notes'] if block['teacher_notes'] else 'None'}\n"
                        )
                        md.write(
                            f"  - *Student Questions:* {block['student_questions'] if block['student_questions'] else 'None'}\n"
                        )
                        md.write(f"  - *Created At:* {block['created_at']}\n")
                        md.write(
                            f"  - *Modified At:* {block['modified_at'] if block['modified_at'] else 'N/A'}\n\n"
                        )

    print(f"✅ Data exported successfully to {md_file}")

except sqlite3.Error as e:
    print(f"❌ An error occurred: {e}")
