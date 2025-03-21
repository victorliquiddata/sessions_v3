import sqlite3
import time
import datetime
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import box
from rich.align import Align
from rich.columns import Columns

# Initialize Rich console
console = Console()


def clear_screen():
    """Clear the terminal screen based on OS."""
    os.system("cls" if os.name == "nt" else "clear")


def transition_screen(title):
    """Clear screen and display a section transition."""
    clear_screen()
    display_header()
    console.print("\n")
    section_title = Panel(
        Align(Text(f"➡️ {title}", style="bold white"), align="center"),
        border_style="magenta",
        box=box.ROUNDED,
        width=80,
    )
    console.print(Align.center(section_title))
    console.print("\n")


def confirm_and_continue():
    """Ask user to press Enter to continue."""
    console.print("\n")
    Prompt.ask("[cyan]Press Enter to continue[/cyan]", default="")


def connect_to_db():
    """Connect to the ESL database."""
    try:
        conn = sqlite3.connect("esl.db")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except sqlite3.Error as e:
        console.print(f"[bold red]Database connection error: {e}[/bold red]")
        exit(1)


def display_header():
    """Display the application header."""
    console.print("\n")
    title = Panel(
        Align(
            Text("📚 ESL Database Homework Generator", style="bold white"),
            align="center",
        ),
        border_style="blue",
        box=box.DOUBLE,
        width=80,
    )
    console.print(Align.center(title))
    console.print("\n")


def export_student_records(conn):
    """Export student records to a Markdown file."""
    transition_screen("Export Student Records")
    student_id = Prompt.ask("Enter the student ID", console=console)

    # First, get student name
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM enrolled_students WHERE id = ?", (student_id,))
        student_result = cursor.fetchone()
        if not student_result:
            console.print(f"⚠️ Student with ID {student_id} not found")
            return
        student_name = student_result["name"]
    except sqlite3.Error as e:
        console.print(f"❌ Error retrieving student name: {e}")
        return

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
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            console.print(f"⚠️ No records found for student ID {student_id}")
            return

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
                courses[course_id]["units"][unit_id] = {
                    "title": unit_title,
                    "lessons": {},
                }

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

        # Create a nice filename similar to homework save logic
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        safe_filename = f"{student_name.replace(' ', '_')}_records_{date_str}.md"

        # Ensure the 'reports' directory exists
        if not os.path.exists("reports"):
            os.makedirs("reports")

        # Define the full path for the file
        file_path = os.path.join("reports", safe_filename)

        with open(file_path, "w", encoding="utf-8") as md:
            md.write(f"# Student {student_id} ({student_name}) Records\n\n")
            md.write(
                f"*Report generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
            )

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

        console.print(
            Panel(
                f"✅ Data exported successfully to {file_path}",
                style="bold green",
                box=box.ROUNDED,
            )
        )

    except sqlite3.Error as e:
        console.print(
            Panel(f"❌ An error occurred: {e}", style="bold red", box=box.ROUNDED)
        )


def get_student_info(conn, student_id):
    """Get student information by ID."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, email, course_id 
            FROM enrolled_students 
            WHERE id = ?
            """,
            (student_id,),
        )
        student = cursor.fetchone()

        if not student:
            console.print(
                Panel(
                    f"No student found with ID {student_id}",
                    style="bold red",
                    box=box.ROUNDED,
                )
            )
            return None

        # Get course information
        cursor.execute(
            """
            SELECT id, name, focus
            FROM courses
            WHERE id = ?
            """,
            (student["course_id"],),
        )
        course = cursor.fetchone()

        return {"student": dict(student), "course": dict(course) if course else None}
    except sqlite3.Error as e:
        console.print(
            Panel(
                f"Error retrieving student information: {e}",
                style="bold red",
                box=box.ROUNDED,
            )
        )
        return None


def display_student_info(student_info):
    """Display formatted student information."""
    student = student_info["student"]
    course = student_info["course"]

    student_table = Table(
        box=box.ROUNDED, border_style="blue", show_header=False, width=80
    )
    student_table.add_column("Field", style="cyan")
    student_table.add_column("Value", style="white")

    student_table.add_row("ID", str(student["id"]))
    student_table.add_row("Name", student["name"])
    student_table.add_row("Email", student["email"])
    student_table.add_row("Course", f"{course['name']} ({course['focus']})")

    console.print(
        Panel(
            student_table,
            title="Student Information",
            border_style="blue",
            box=box.ROUNDED,
        )
    )


def get_lesson_info(conn, lesson_id):
    """Get comprehensive lesson information by ID."""
    try:
        cursor = conn.cursor()

        # Get lesson details
        cursor.execute(
            """
            SELECT l.id, l.title, l.grammar_focus, l.vocabulary_focus, l.context,
                   u.unit_number, u.title as unit_title, 
                   c.id as course_id, c.name as course_name
            FROM lessons l
            JOIN units u ON l.unit_id = u.id
            JOIN courses c ON u.course_id = c.id
            WHERE l.id = ?
            """,
            (lesson_id,),
        )
        lesson = cursor.fetchone()

        if not lesson:
            console.print(
                Panel(
                    f"No lesson found with ID {lesson_id}",
                    style="bold red",
                    box=box.ROUNDED,
                )
            )
            return None

        # Get vocabulary for the lesson
        cursor.execute(
            """
            SELECT word_or_phrase, definition, example_usage
            FROM vocabulary
            WHERE lesson_id = ?
            """,
            (lesson_id,),
        )
        vocabulary = cursor.fetchall()

        # Get grammar rules for the lesson
        cursor.execute(
            """
            SELECT rule, example
            FROM grammar_rules
            WHERE lesson_id = ?
            """,
            (lesson_id,),
        )
        grammar_rules = cursor.fetchall()

        # Get blocks for the lesson
        cursor.execute(
            """
            SELECT id, title, description, activity_type, content
            FROM blocks
            WHERE lesson_id = ?
            ORDER BY block_number
            """,
            (lesson_id,),
        )
        blocks = cursor.fetchall()

        # Get resources for the lesson
        cursor.execute(
            """
            SELECT resource_type, description, url_or_path
            FROM resources
            WHERE lesson_id = ?
            """,
            (lesson_id,),
        )
        resources = cursor.fetchall()

        return {
            "lesson": dict(lesson),
            "vocabulary": [dict(v) for v in vocabulary],
            "grammar_rules": [dict(g) for g in grammar_rules],
            "blocks": [dict(b) for b in blocks],
            "resources": [dict(r) for r in resources],
        }
    except sqlite3.Error as e:
        console.print(
            Panel(
                f"Error retrieving lesson information: {e}",
                style="bold red",
                box=box.ROUNDED,
            )
        )
        return None


def display_lesson_info(lesson_info):
    """Display formatted lesson information."""
    lesson = lesson_info["lesson"]

    lesson_table = Table(
        box=box.ROUNDED, border_style="green", show_header=False, width=80
    )
    lesson_table.add_column("Field", style="cyan")
    lesson_table.add_column("Value", style="white")

    lesson_table.add_row("ID", str(lesson["id"]))
    lesson_table.add_row("Title", lesson["title"])
    lesson_table.add_row("Course", lesson["course_name"])
    lesson_table.add_row("Unit", f"{lesson['unit_number']}: {lesson['unit_title']}")
    lesson_table.add_row("Grammar Focus", lesson["grammar_focus"])
    lesson_table.add_row("Vocabulary Focus", lesson["vocabulary_focus"])

    console.print(
        Panel(
            lesson_table,
            title="Lesson Information",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    # Display summary of content
    summary = Columns(
        [
            Panel(
                f"[cyan]Vocabulary:[/cyan] {len(lesson_info['vocabulary'])} items",
                box=box.ROUNDED,
            ),
            Panel(
                f"[cyan]Grammar Rules:[/cyan] {len(lesson_info['grammar_rules'])} rules",
                box=box.ROUNDED,
            ),
            Panel(
                f"[cyan]Activity Blocks:[/cyan] {len(lesson_info['blocks'])} blocks",
                box=box.ROUNDED,
            ),
            Panel(
                f"[cyan]Resources:[/cyan] {len(lesson_info['resources'])} items",
                box=box.ROUNDED,
            ),
        ],
        width=19,
        equal=True,
    )

    console.print(summary)


def get_student_lesson_record(conn, student_id, lesson_id):
    """Get student's record for this specific lesson if it exists."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, completion_date, score, feedback
            FROM lesson_records
            WHERE student_id = ? AND lesson_id = ?
            """,
            (student_id, lesson_id),
        )
        record = cursor.fetchone()

        if record:
            # Get block records if they exist
            cursor.execute(
                """
                SELECT br.id, br.student_speech_notes, br.teacher_notes, br.student_questions,
                       b.title as block_title, b.activity_type
                FROM block_records br
                JOIN blocks b ON br.block_id = b.id
                WHERE br.lesson_record_id = ?
                """,
                (record["id"],),
            )
            block_records = cursor.fetchall()

            return {
                "record": dict(record),
                "block_records": [dict(br) for br in block_records],
            }
        return None
    except sqlite3.Error as e:
        console.print(
            Panel(
                f"Error retrieving lesson record: {e}",
                style="bold red",
                box=box.ROUNDED,
            )
        )
        return None


def display_student_lesson_record(lesson_record):
    """Display formatted student lesson record."""
    if not lesson_record:
        console.print(
            Panel(
                "No previous lesson record found for this student and lesson",
                style="yellow",
                box=box.ROUNDED,
            )
        )
        return

    record = lesson_record["record"]

    # Format completion date if it exists
    completion_date = record.get("completion_date", "Not completed")
    if completion_date and completion_date != "Not completed":
        # Fixed code
        try:
            completion_date = datetime.datetime.fromisoformat(completion_date).strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            # Specifically catch ValueError which is raised for invalid date formats
            pass

    record_table = Table(
        box=box.ROUNDED, border_style="yellow", show_header=False, width=80
    )
    record_table.add_column("Field", style="cyan")
    record_table.add_column("Value", style="white")

    record_table.add_row("Record ID", str(record["id"]))
    record_table.add_row("Completion Date", completion_date)
    record_table.add_row("Score", str(record.get("score", "Not scored")))

    feedback = record.get("feedback", "No feedback provided")
    record_table.add_row("Feedback", f"\n{feedback}\n")

    console.print(
        Panel(
            record_table,
            title="Previous Lesson Record",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    # Display block records if they exist
    if lesson_record.get("block_records"):
        console.print(
            Panel(
                f"[cyan]Block Records Available:[/cyan] {len(lesson_record['block_records'])} blocks",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )


def generate_homework(student_info, lesson_info, lesson_record):
    """Generate a personalized homework assignment based on lesson and student progress."""
    student = student_info["student"]
    course = student_info["course"]
    lesson = lesson_info["lesson"]

    # Build the homework content
    homework = f"# 📚 Personalized Homework for {student['name']}\n\n"
    homework += f"**Course:** {course['name']}\n"
    homework += f"**Lesson:** {lesson['title']} (Unit {lesson['unit_number']}: {lesson['unit_title']})\n"
    homework += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"

    # Include lesson context
    if lesson["context"]:
        homework += f"## 🎯 Lesson Overview\n{lesson['context']}\n\n"

    # Include feedback if available
    if lesson_record and lesson_record["record"].get("feedback"):
        homework += f"## 📝 Feedback from Your Last Class\n{lesson_record['record']['feedback']}\n\n"

    # Include student speech notes if available
    if lesson_record and lesson_record.get("block_records"):
        homework += "## 🗣️ Your Speaking Notes\n"
        for block in lesson_record["block_records"]:
            if block["student_speech_notes"]:
                homework += f"### Activity: {block['block_title']}\n"
                homework += f"{block['student_speech_notes']}\n\n"

                # Add dynamic practice recommendations based on activity type
                activity_type = block["activity_type"].lower()
                if activity_type == "speaking":
                    homework += "**Practice recommendation:** Record yourself speaking about this topic for 3-5 minutes and listen for areas to improve.\n\n"
                elif activity_type == "writing":
                    homework += "**Practice recommendation:** Write a short paragraph expanding on this topic.\n\n"
                elif activity_type == "reading":
                    homework += "**Practice recommendation:** Read additional materials on this topic and summarize them.\n\n"
                elif activity_type == "listening":
                    homework += "**Practice recommendation:** Listen to a related audio resource and take notes.\n\n"
                else:
                    homework += "**Practice recommendation:** Review the topic and prepare questions for the next class.\n\n"

    # Vocabulary review
    if lesson_info["vocabulary"]:
        homework += "## 📘 Vocabulary Review\n"
        homework += "Practice using these words and phrases from our lesson:\n\n"
        for item in lesson_info["vocabulary"]:
            homework += f"- **{item['word_or_phrase']}**: {item['definition']}\n"
            if item["example_usage"]:
                homework += f"  Example: *{item['example_usage']}*\n"
        homework += "\n"

    # Grammar practice
    if lesson_info["grammar_rules"]:
        homework += "## 📖 Grammar Practice\n"
        homework += f"Based on our focus on {lesson['grammar_focus']}, practice these rules:\n\n"
        for rule in lesson_info["grammar_rules"]:
            homework += f"- **Rule**: {rule['rule']}\n"
            if rule["example"]:
                homework += f"  Example: *{rule['example']}*\n"
        homework += "\nCreate 3-5 original sentences using these grammar rules.\n\n"

    # Structured activities based on blocks
    if lesson_info["blocks"]:
        homework += "## 📋 Structured Activities\n"
        for block in lesson_info["blocks"]:
            homework += f"### 🏡 {block['title']} ({block['activity_type']})\n"
            homework += f"{block['description']}\n\n"
            homework += f"**Task:** {block['content']}\n\n"

    # Additional resources
    if lesson_info["resources"]:
        homework += "## 🔗 Additional Resources\n"
        homework += "Use these resources to further practice what we've learned:\n\n"
        for resource in lesson_info["resources"]:
            homework += f"- **{resource['description']}** ({resource['resource_type']}): {resource['url_or_path']}\n"
        homework += "\n"

    # General practice suggestions
    homework += "## ✅ General Practice\n"
    homework += "1. Review the vocabulary and grammar points from this lesson.\n"
    homework += "2. Practice using new vocabulary in conversations or writing.\n"
    homework += (
        "3. Complete any exercises from your workbook related to this material.\n"
    )
    homework += "4. Prepare questions about anything you find challenging for our next class.\n\n"

    return homework


def save_homework(homework, student_name, lesson_title):
    """Save the homework to a text file in the 'homeworks' folder."""
    # Create a safe filename
    safe_filename = (
        f"{student_name.replace(' ', '_')}_{lesson_title.replace(' ', '_')}_homework.md"
    )

    # Ensure the 'homeworks' directory exists
    if not os.path.exists("homeworks"):
        os.makedirs("homeworks")

    # Define the full path for the file
    file_path = os.path.join("homeworks", safe_filename)

    # Fixed code
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(homework)
        console.print(
            Panel(f"Homework saved to {file_path}", style="bold green", box=box.ROUNDED)
        )
        return file_path
    except (IOError, OSError) as e:
        # More specific exceptions for file operations
        console.print(
            Panel(f"Error saving homework: {e}", style="bold red", box=box.ROUNDED)
        )
        return None


def display_homework_preview(homework):
    """Display a formatted preview of the homework."""
    # Create a shortened version for preview
    first_section = homework.split("\n\n")[0] + "\n\n"  # Get header

    # Add a few more sections, limiting to about 15 lines
    sections = homework.split("##")
    preview = first_section + "##" + sections[1] if len(sections) > 1 else first_section

    # Truncate if too long
    preview_lines = preview.split("\n")
    if len(preview_lines) > 15:
        preview = "\n".join(preview_lines[:15]) + "\n\n[...content continues...]"

    console.print(
        Panel(
            Markdown(preview),
            title="Homework Preview",
            subtitle="(partial content shown)",
            border_style="green",
            box=box.ROUNDED,
            width=80,
        )
    )


def display_homework_actions(homework, student_info, lesson_info):
    """Display action menu for homework."""
    actions = [
        ("Save to file", "Save the homework to a markdown file"),
        ("Full Preview", "View the complete homework in the console"),
        ("Edit & Regenerate", "Modify and regenerate the homework"),
        ("Exit", "Exit the program"),
    ]

    action_table = Table(box=box.ROUNDED, border_style="blue", show_header=True)
    action_table.add_column("Option", style="cyan")
    action_table.add_column("Description", style="white")

    for i, (action, desc) in enumerate(actions, 1):
        action_table.add_row(f"{i}. {action}", desc)

    console.print(
        Panel(
            action_table,
            title="Available Actions",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    choice = Prompt.ask("Choose an action", choices=["1", "2", "3", "4"], default="1")

    if choice == "1":
        # Line 745 - Fixed
        save_homework(
            homework, student_info["student"]["name"], lesson_info["lesson"]["title"]
        )
        return True
    elif choice == "2":
        # Full preview
        console.print(
            Panel(
                Markdown(homework),
                title="Complete Homework",
                border_style="green",
                box=box.ROUNDED,
                width=80,
                padding=(1, 2),
            )
        )
        return True
    elif choice == "3":
        # Edit & Regenerate (simplified - would need more implementation)
        console.print(
            Panel(
                "Edit & Regenerate feature not implemented in this demo",
                style="yellow",
                box=box.ROUNDED,
            )
        )
        return True
    else:
        # Exit
        return False


def search_students(conn, search_term):
    """Search for students by name or email."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, email, course_id
            FROM enrolled_students
            WHERE name LIKE ? OR email LIKE ?
            """,
            (f"%{search_term}%", f"%{search_term}%"),
        )
        students = cursor.fetchall()

        if not students:
            console.print(
                Panel("No matching students found", style="yellow", box=box.ROUNDED)
            )
            return None

        return [dict(s) for s in students]
    except sqlite3.Error as e:
        console.print(
            Panel(f"Error searching students: {e}", style="bold red", box=box.ROUNDED)
        )
        return None


def display_search_results(students, conn):
    """Display search results and allow selection."""
    if not students:
        return None

    results_table = Table(box=box.ROUNDED, border_style="blue", show_header=True)
    results_table.add_column("ID", style="cyan")
    results_table.add_column("Name", style="white")
    results_table.add_column("Email", style="white")
    results_table.add_column("Course", style="white")

    # Get course names
    cursor = conn.cursor()
    for student in students:
        course_name = "Unknown"
        cursor.execute("SELECT name FROM courses WHERE id = ?", (student["course_id"],))
        course = cursor.fetchone()
        if course:
            course_name = course["name"]

        results_table.add_row(
            str(student["id"]), student["name"], student["email"], course_name
        )

    console.print(
        Panel(
            results_table, title="Search Results", border_style="blue", box=box.ROUNDED
        )
    )

    # Let user select a student
    if len(students) == 1:
        return students[0]["id"]

    student_id = Prompt.ask(
        "Select a student ID or press Enter to search again", default=""
    )

    if student_id and student_id.isdigit():
        # Verify the ID is in the list
        valid_ids = [str(s["id"]) for s in students]
        if student_id in valid_ids:
            return student_id
        else:
            console.print(
                Panel("Invalid student ID selected", style="yellow", box=box.ROUNDED)
            )
            return None

    return None


def search_lessons(conn, search_term):
    """Search for lessons by title or unit."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT les.id, les.title, u.unit_number, u.title as unit_title, c.name as course_name
            FROM lessons les
            JOIN units u ON les.unit_id = u.id
            JOIN courses c ON u.course_id = c.id
            WHERE les.title LIKE ? OR u.title LIKE ?
            """,
            (f"%{search_term}%", f"%{search_term}%"),
        )
        lessons = cursor.fetchall()

        if not lessons:
            console.print(
                Panel("No matching lessons found", style="yellow", box=box.ROUNDED)
            )
            return None

        return [dict(lesson) for lesson in lessons]
    except sqlite3.Error as e:
        console.print(
            Panel(f"Error searching lessons: {e}", style="bold red", box=box.ROUNDED)
        )
        return None


def display_lesson_search_results(lessons):
    """Display lesson search results and allow selection."""
    if not lessons:
        return None

    results_table = Table(box=box.ROUNDED, border_style="green", show_header=True)
    results_table.add_column("ID", style="cyan")
    results_table.add_column("Lesson Title", style="white")
    results_table.add_column("Unit", style="white")
    results_table.add_column("Course", style="white")

    for lesson in lessons:
        results_table.add_row(
            str(lesson["id"]),
            lesson["title"],
            f"{lesson['unit_number']}: {lesson['unit_title']}",
            lesson["course_name"],
        )

    console.print(
        Panel(
            results_table,
            title="Lesson Search Results",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    # Let user select a lesson
    if len(lessons) == 1:
        return lessons[0]["id"]

    lesson_id = Prompt.ask(
        "Select a lesson ID or press Enter to search again", default=""
    )

    if lesson_id and lesson_id.isdigit():
        # Verify the ID is in the list
        valid_ids = [str(lesson["id"]) for lesson in lessons]
        if lesson_id in valid_ids:
            return lesson_id
        else:
            console.print(
                Panel("Invalid lesson ID selected", style="yellow", box=box.ROUNDED)
            )
            return None

    return None


def display_main_menu():
    """Display the main menu options."""
    menu_table = Table(box=box.ROUNDED, border_style="blue", show_header=True)
    menu_table.add_column("Option", style="cyan")
    menu_table.add_column("Description", style="white")

    menu_options = [
        ("Generate Homework", "Create personalized homework for a student"),
        ("Export Student Records", "Export student data to Markdown"),
        ("Search Students", "Find and view student information"),
        ("Search Lessons", "Find and view lesson information"),
        ("Exit", "Exit the application"),
    ]

    for i, (option, desc) in enumerate(menu_options, 1):
        menu_table.add_row(f"{i}. {option}", desc)

    console.print(
        Panel(
            menu_table,
            title="Main Menu",
            border_style="blue",
            box=box.ROUNDED,
        )
    )


def main():
    conn = connect_to_db()
    clear_screen()
    display_header()

    while True:
        # Display the main menu
        display_main_menu()
        choice = Prompt.ask(
            "Choose an option", choices=["1", "2", "3", "4", "5"], default="1"
        )

        if choice == "1":
            # Generate Homework
            transition_screen("Homework Generation")
            generate_homework_flow(conn)
        elif choice == "2":
            # Export Student Records
            transition_screen("Export Student Records")
            export_student_records(conn)
            confirm_and_continue()
        elif choice == "3":
            # Search Students
            transition_screen("Student Search")
            search_students_flow(conn)
        elif choice == "4":
            # Search Lessons
            transition_screen("Lesson Search")
            search_lessons_flow(conn)
        elif choice == "5":
            # Exit
            break

    conn.close()
    transition_screen("Session Complete")
    console.print(
        Panel(
            "Thank you for using the ESL Homework Generator",
            style="bold green",
            box=box.ROUNDED,
        )
    )


def generate_homework_flow(conn):
    """Flow for generating homework."""
    # Get student ID (enhanced with search)
    while True:
        choice = Prompt.ask(
            "Enter student ID, search by name, or type 'search'", console=console
        )

        if choice.lower() == "search":
            search_term = Prompt.ask("Enter student name or email to search")
            students = search_students(conn, search_term)
            student_id = display_search_results(students, conn)
            if student_id:
                break
        elif choice.isdigit():
            student_id = choice
            break
        else:
            # Assume they entered a name to search
            students = search_students(conn, choice)
            student_id = display_search_results(students, conn)
            if student_id:
                break

    student_info = get_student_info(conn, student_id)
    if not student_info:
        return
    transition_screen("Student Information")
    display_student_info(student_info)
    confirm_and_continue()

    # Get lesson ID (enhanced with search)
    while True:
        console.print("\n[bold cyan]Lesson Selection[/bold cyan]")
        choice = Prompt.ask(
            "Enter lesson ID, search by title, or type 'search'", console=console
        )

        if choice.lower() == "search":
            search_term = Prompt.ask("Enter lesson title or unit to search")
            lessons = search_lessons(conn, search_term)
            lesson_id = display_lesson_search_results(lessons)
            if lesson_id:
                break
        elif choice.isdigit():
            lesson_id = choice
            break
        else:
            # Assume they entered a title to search
            lessons = search_lessons(conn, choice)
            lesson_id = display_lesson_search_results(lessons)
            if lesson_id:
                break

    lesson_info = get_lesson_info(conn, lesson_id)
    if not lesson_info:
        return
    transition_screen("Lesson Information")
    display_lesson_info(lesson_info)

    # Check if this student's course matches the lesson's course
    if student_info["course"]["id"] != lesson_info["lesson"]["course_id"]:
        console.print(
            Panel(
                f"This lesson is not part of {student_info['student']['name']}'s current course.",
                title="⚠️ Course Mismatch",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        proceed = Confirm.ask(
            "Do you want to proceed anyway?", default=False, console=console
        )
        if not proceed:
            return

    # Get student's record for this lesson if it exists
    lesson_record = get_student_lesson_record(conn, student_id, lesson_id)
    display_student_lesson_record(lesson_record)

    # Generate the homework with visual progress
    console.print("\n[bold cyan]Generating Homework[/bold cyan]")
    transition_screen("Homework Generation")
    with Progress(
        "[progress.description]{task.description}",
        "[progress.percentage]{task.percentage:>3.0f}%",
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Generating personalized homework...", total=100)
    # Line 1097 - Fixed
    for _ in range(100):
        progress.update(task, advance=1)
        time.sleep(0.01)  # Simulate work being done

    homework = generate_homework(student_info, lesson_info, lesson_record)

    # Display preview and action menu
    transition_screen("Homework Management")
    display_homework_preview(homework)

    # Loop for actions
    while display_homework_actions(homework, student_info, lesson_info):
        display_homework_preview(homework)


def search_students_flow(conn):
    """Flow for searching students."""
    search_term = Prompt.ask("Enter student name or email to search")
    students = search_students(conn, search_term)
    student_id = display_search_results(students, conn)
    if student_id:
        student_info = get_student_info(conn, student_id)
        if student_info:
            transition_screen("Student Information")
            display_student_info(student_info)
            confirm_and_continue()


def search_lessons_flow(conn):
    """Flow for searching lessons."""
    search_term = Prompt.ask("Enter lesson title or unit to search")
    lessons = search_lessons(conn, search_term)
    lesson_id = display_lesson_search_results(lessons)
    if lesson_id:
        lesson_info = get_lesson_info(conn, lesson_id)
        if lesson_info:
            transition_screen("Lesson Information")
            display_lesson_info(lesson_info)
            confirm_and_continue()


if __name__ == "__main__":
    main()
