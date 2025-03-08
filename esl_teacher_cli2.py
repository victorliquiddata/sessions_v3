#!/usr/bin/env python3
import sqlite3
import os
import sys
from datetime import datetime
import argparse
from tabulate import tabulate  # You might need to install this: pip install tabulate
import textwrap
import time
import shutil


class ESLTeacherCLI:
    def __init__(self, db_path="esl.db"):
        """Initialize the CLI with database connection"""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.current_student = None
        self.current_course = None
        self.current_unit = None
        self.current_lesson = None
        self.current_block = None
        self.current_lesson_record = None

        # Get terminal size for better UI formatting
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()

    def connect_db(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            return True
        except sqlite3.Error as e:
            self.print_error(f"Database connection error: {e}")
            return False

    def close_db(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def execute_query(self, query, params=(), fetch_mode="all"):
        """Execute SQL query and return results based on fetch_mode"""
        try:
            self.cursor.execute(query, params)

            if fetch_mode == "all":
                return self.cursor.fetchall()
            elif fetch_mode == "one":
                return self.cursor.fetchone()
            else:
                self.connection.commit()
                return None
        except sqlite3.Error as e:
            self.print_error(f"Query execution error: {e}")
            self.print_error(f"Query: {query}")
            self.print_error(f"Parameters: {params}")
            return None

    def clear_screen(self):
        """Clear the terminal screen based on OS"""
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self, title):
        """Print a formatted header"""
        self.clear_screen()
        print("\n" + "═" * self.terminal_width)
        print(f"{'ESL TEACHER ASSISTANT':^{self.terminal_width}}")
        print(f"{title:^{self.terminal_width}}")
        print("═" * self.terminal_width + "\n")

    def print_footer(self):
        """Print a formatted footer"""
        print("\n" + "═" * self.terminal_width)
        if self.current_student:
            print(f"Student: {self.current_student['name']} | ", end="")
        if self.current_course:
            print(f"Course: {self.current_course['name']} | ", end="")
        if self.current_unit:
            print(f"Unit: {self.current_unit['unit_number']} | ", end="")
        if self.current_lesson:
            print(f"Lesson: {self.current_lesson['lesson_number']}")
        else:
            print()
        print("═" * self.terminal_width)

    def print_error(self, message):
        """Print error message with formatting"""
        print("\n❌ " + "=" * 15 + " ERROR " + "=" * 15)
        print(f"  {message}")
        print("=" * 40 + "\n")

    def print_success(self, message):
        """Print success message with formatting"""
        print("\n✅ " + "=" * 15 + " SUCCESS " + "=" * 15)
        print(f"  {message}")
        print("=" * 40 + "\n")

    def display_splash_screen(self):
        """Display a splash screen with ASCII art"""
        self.clear_screen()
        splash = """
        ███████╗███████╗██╗         ████████╗███████╗ █████╗  ██████╗██╗  ██╗███████╗██████╗ 
        ██╔════╝██╔════╝██║         ╚══██╔══╝██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗
        █████╗  ███████╗██║            ██║   █████╗  ███████║██║     ███████║█████╗  ██████╔╝
        ██╔══╝  ╚════██║██║            ██║   ██╔══╝  ██╔══██║██║     ██╔══██║██╔══╝  ██╔══██╗
        ███████╗███████║███████╗       ██║   ███████╗██║  ██║╚██████╗██║  ██║███████╗██║  ██║
        ╚══════╝╚══════╝╚══════╝       ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                                                                                          
         █████╗ ███████╗███████╗██╗███████╗████████╗ █████╗ ███╗   ██╗████████╗
        ██╔══██╗██╔════╝██╔════╝██║██╔════╝╚══██╔══╝██╔══██╗████╗  ██║╚══██╔══╝
        ███████║███████╗███████╗██║███████╗   ██║   ███████║██╔██╗ ██║   ██║   
        ██╔══██║╚════██║╚════██║██║╚════██║   ██║   ██╔══██║██║╚██╗██║   ██║   
        ██║  ██║███████║███████║██║███████║   ██║   ██║  ██║██║ ╚████║   ██║   
        ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   
                                                                                
        """
        print(splash)
        print(f"{'Your Digital Teaching Companion':^{self.terminal_width}}")
        print(f"{'Version 1.0.0':^{self.terminal_width}}")
        print(f"{'-' * 40:^{self.terminal_width}}")
        print(f"{'Loading...':^{self.terminal_width}}")

        # Animated loading bar
        bar_width = 40
        for i in range(bar_width + 1):
            progress = "█" * i + "░" * (bar_width - i)
            sys.stdout.write(f"\r{progress:^{self.terminal_width}}")
            sys.stdout.flush()
            time.sleep(0.03)
        print("\n")

    def list_students(self):
        """List all enrolled students"""
        self.print_header("ENROLLED STUDENTS")

        query = """
        SELECT es.id, es.name, es.email, c.name as course_name
        FROM enrolled_students es
        JOIN courses c ON es.course_id = c.id
        ORDER BY es.name
        """
        students = self.execute_query(query)

        if not students:
            print("No students found.")
            return

        table_data = [
            (s["id"], s["name"], s["email"], s["course_name"]) for s in students
        ]
        headers = ["ID", "Name", "Email", "Course"]

        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        self.print_footer()

    def select_student(self, student_id):
        """Select a student to work with"""
        query = """
        SELECT es.*, c.name as course_name 
        FROM enrolled_students es
        JOIN courses c ON es.course_id = c.id
        WHERE es.id = ?
        """
        student = self.execute_query(query, (student_id,), "one")

        if not student:
            self.print_error(f"No student found with ID {student_id}")
            return False

        self.current_student = dict(student)
        self.current_course = {
            "id": student["course_id"],
            "name": student["course_name"],
        }
        self.print_success(
            f"Selected student: {self.current_student['name']} (Course: {self.current_course['name']})"
        )
        return True

    def list_units(self):
        """List all units for the current course"""
        if not self.current_course:
            self.print_error("No course selected. Please select a student first.")
            return

        self.print_header(f"UNITS FOR {self.current_course['name'].upper()}")

        query = """
        SELECT id, unit_number, title, description
        FROM units
        WHERE course_id = ?
        ORDER BY unit_number
        """
        units = self.execute_query(query, (self.current_course["id"],))

        if not units:
            print(f"No units found for course '{self.current_course['name']}'.")
            return

        table_data = [
            (
                u["id"],
                u["unit_number"],
                u["title"],
                textwrap.shorten(u["description"] or "", width=40),
            )
            for u in units
        ]
        headers = ["ID", "Number", "Title", "Description"]

        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        self.print_footer()

    def select_unit(self, unit_id):
        """Select a unit to work with"""
        query = "SELECT * FROM units WHERE id = ?"
        unit = self.execute_query(query, (unit_id,), "one")

        if not unit:
            self.print_error(f"No unit found with ID {unit_id}")
            return False

        self.current_unit = dict(unit)
        self.print_success(
            f"Selected unit: {self.current_unit['title']} (Unit {self.current_unit['unit_number']})"
        )
        return True

    def list_lessons(self):
        """List all lessons for the current unit"""
        if not self.current_unit:
            self.print_error("No unit selected. Please select a unit first.")
            return

        self.print_header(
            f"LESSONS FOR UNIT {self.current_unit['unit_number']}: {self.current_unit['title'].upper()}"
        )

        query = """
        SELECT l.id, l.lesson_number, l.title, l.grammar_focus, l.vocabulary_focus,
               CASE WHEN lr.id IS NOT NULL THEN 'Completed' ELSE 'Not Started' END as status
        FROM lessons l
        LEFT JOIN lesson_records lr ON l.id = lr.lesson_id AND lr.student_id = ?
        WHERE l.unit_id = ?
        ORDER BY l.lesson_number
        """
        lessons = self.execute_query(
            query, (self.current_student["id"], self.current_unit["id"])
        )

        if not lessons:
            print(f"No lessons found for unit '{self.current_unit['title']}'.")
            return

        table_data = [
            (
                l["id"],
                l["lesson_number"],
                l["title"],
                textwrap.shorten(l["grammar_focus"] or "", width=30),
                textwrap.shorten(l["vocabulary_focus"] or "", width=30),
                l["status"],
            )
            for l in lessons
        ]
        headers = [
            "ID",
            "Number",
            "Title",
            "Grammar Focus",
            "Vocabulary Focus",
            "Status",
        ]

        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        self.print_footer()

    def select_lesson(self, lesson_id):
        """Select a lesson to work with"""
        query = "SELECT * FROM lessons WHERE id = ?"
        lesson = self.execute_query(query, (lesson_id,), "one")

        if not lesson:
            self.print_error(f"No lesson found with ID {lesson_id}")
            return False

        self.current_lesson = dict(lesson)

        # Check if there's an existing lesson record
        query = """
        SELECT * FROM lesson_records 
        WHERE student_id = ? AND lesson_id = ?
        """
        lesson_record = self.execute_query(
            query, (self.current_student["id"], lesson_id), "one"
        )

        if lesson_record:
            self.current_lesson_record = dict(lesson_record)
            self.print_success(
                f"Selected lesson: {self.current_lesson['title']} (Status: Previously started)"
            )
        else:
            # Create a new lesson_record
            query = """
            INSERT INTO lesson_records (student_id, lesson_id)
            VALUES (?, ?)
            """
            self.execute_query(query, (self.current_student["id"], lesson_id), "commit")

            # Get the newly created record
            query = (
                "SELECT * FROM lesson_records WHERE student_id = ? AND lesson_id = ?"
            )
            lesson_record = self.execute_query(
                query, (self.current_student["id"], lesson_id), "one"
            )
            self.current_lesson_record = dict(lesson_record)
            self.print_success(
                f"Selected lesson: {self.current_lesson['title']} (Status: New session)"
            )

        return True

    def display_lesson_details(self):
        """Display comprehensive details about the current lesson"""
        if not self.current_lesson:
            self.print_error("No lesson selected. Please select a lesson first.")
            return

        self.print_header(
            f"LESSON {self.current_lesson['lesson_number']}: {self.current_lesson['title']}"
        )

        # Get grammar rules
        query = "SELECT * FROM grammar_rules WHERE lesson_id = ?"
        grammar_rules = self.execute_query(query, (self.current_lesson["id"],))

        # Get vocabulary
        query = "SELECT * FROM vocabulary WHERE lesson_id = ?"
        vocabulary = self.execute_query(query, (self.current_lesson["id"],))

        # Get resources
        query = "SELECT * FROM resources WHERE lesson_id = ?"
        resources = self.execute_query(query, (self.current_lesson["id"],))

        # Display lesson info in formatted boxes
        context_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 📝 CONTEXT                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
        """

        grammar_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 GRAMMAR FOCUS                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
        """

        vocab_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 📚 VOCABULARY FOCUS                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
        """

        # Format and print context
        context = self.current_lesson["context"] or "No context provided."
        wrapped_context = "\n│ ".join(textwrap.wrap(context, width=70))
        print(context_box % wrapped_context)

        # Format and print grammar focus
        grammar = self.current_lesson["grammar_focus"] or "No grammar focus specified."
        wrapped_grammar = "\n│ ".join(textwrap.wrap(grammar, width=70))
        print(grammar_box % wrapped_grammar)

        # Format and print vocabulary focus
        vocab = (
            self.current_lesson["vocabulary_focus"] or "No vocabulary focus specified."
        )
        wrapped_vocab = "\n│ ".join(textwrap.wrap(vocab, width=70))
        print(vocab_box % wrapped_vocab)

        if grammar_rules:
            print("\n" + "─" * 80)
            print("📘 GRAMMAR RULES")
            print("─" * 80)
            for rule in grammar_rules:
                print(f"\n• {rule['rule']}")
                if rule["example"]:
                    print(f"  Example: {rule['example']}")

        if vocabulary:
            print("\n" + "─" * 80)
            print("📖 VOCABULARY LIST")
            print("─" * 80)
            vocab_data = [
                (
                    v["word_or_phrase"],
                    v["definition"] or "No definition",
                    v["example_usage"] or "No example",
                )
                for v in vocabulary
            ]
            headers = ["Word/Phrase", "Definition", "Example Usage"]
            print(tabulate(vocab_data, headers=headers, tablefmt="fancy_grid"))

        if resources:
            print("\n" + "─" * 80)
            print("🔗 RESOURCES")
            print("─" * 80)
            for res in resources:
                print(
                    f"\n• {res['resource_type']}: {res['description'] or 'No description'}"
                )
                print(f"  Location: {res['url_or_path']}")

        self.print_footer()

    def list_blocks(self):
        """List all blocks for the current lesson"""
        if not self.current_lesson:
            self.print_error("No lesson selected. Please select a lesson first.")
            return

        self.print_header(
            f"BLOCKS FOR LESSON {self.current_lesson['lesson_number']}: {self.current_lesson['title'].upper()}"
        )

        query = """
        SELECT b.id, b.block_number, b.title, b.activity_type,
               CASE WHEN br.id IS NOT NULL THEN 'Completed' ELSE 'Not Started' END as status
        FROM blocks b
        LEFT JOIN block_records br ON b.id = br.block_id AND br.lesson_record_id = ?
        WHERE b.lesson_id = ?
        ORDER BY b.block_number
        """
        blocks = self.execute_query(
            query, (self.current_lesson_record["id"], self.current_lesson["id"])
        )

        if not blocks:
            print(f"No blocks found for lesson '{self.current_lesson['title']}'.")
            return

        # Create a more visual representation with emojis for activity types
        table_data = []
        for b in blocks:
            activity_icon = "🗣️"  # Default for speaking
            if b["activity_type"]:
                if "read" in b["activity_type"].lower():
                    activity_icon = "📖"
                elif "writ" in b["activity_type"].lower():
                    activity_icon = "✏️"
                elif "listen" in b["activity_type"].lower():
                    activity_icon = "👂"
                elif "speak" in b["activity_type"].lower():
                    activity_icon = "🗣️"
                elif "game" in b["activity_type"].lower():
                    activity_icon = "🎮"
                elif (
                    "quiz" in b["activity_type"].lower()
                    or "test" in b["activity_type"].lower()
                ):
                    activity_icon = "📝"

            status_icon = "✅" if b["status"] == "Completed" else "⏳"

            table_data.append(
                (
                    b["id"],
                    f"{b['block_number']}",
                    b["title"],
                    f"{activity_icon} {b['activity_type'] or 'Not specified'}",
                    f"{status_icon} {b['status']}",
                )
            )

        headers = ["ID", "Number", "Title", "Activity Type", "Status"]

        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        self.print_footer()

    def select_block(self, block_id):
        """Select a block to work with"""
        query = "SELECT * FROM blocks WHERE id = ?"
        block = self.execute_query(query, (block_id,), "one")

        if not block:
            self.print_error(f"No block found with ID {block_id}")
            return False

        self.current_block = dict(block)

        # Check if there's an existing block record
        query = """
        SELECT * FROM block_records 
        WHERE lesson_record_id = ? AND block_id = ?
        """
        block_record = self.execute_query(
            query, (self.current_lesson_record["id"], block_id), "one"
        )

        if not block_record:
            # Create a new block_record
            query = """
            INSERT INTO block_records (lesson_record_id, block_id, created_at)
            VALUES (?, ?, datetime('now'))
            """
            self.execute_query(
                query, (self.current_lesson_record["id"], block_id), "commit"
            )

        self.print_success(
            f"Selected block: {self.current_block['title']} (Block {self.current_block['block_number']})"
        )
        return True

    def display_block_details(self):
        """Display details about the current block"""
        if not self.current_block:
            self.print_error("No block selected. Please select a block first.")
            return

        self.print_header(
            f"BLOCK {self.current_block['block_number']}: {self.current_block['title']}"
        )

        query = """
        SELECT * FROM block_records
        WHERE lesson_record_id = ? AND block_id = ?
        """
        block_record = self.execute_query(
            query, (self.current_lesson_record["id"], self.current_block["id"]), "one"
        )

        # Display activity type with icon
        activity_icon = "🗣️"  # Default for speaking
        if self.current_block["activity_type"]:
            if "read" in self.current_block["activity_type"].lower():
                activity_icon = "📖"
            elif "writ" in self.current_block["activity_type"].lower():
                activity_icon = "✏️"
            elif "listen" in self.current_block["activity_type"].lower():
                activity_icon = "👂"
            elif "speak" in self.current_block["activity_type"].lower():
                activity_icon = "🗣️"
            elif "game" in self.current_block["activity_type"].lower():
                activity_icon = "🎮"
            elif (
                "quiz" in self.current_block["activity_type"].lower()
                or "test" in self.current_block["activity_type"].lower()
            ):
                activity_icon = "📝"

        print(
            f"\n{activity_icon} Activity Type: {self.current_block['activity_type'] or 'Not specified'}"
        )

        # Display description and content in nice boxes
        desc_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 📋 DESCRIPTION                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
        """

        content_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 📄 CONTENT                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
        """

        # Format and print description
        description = self.current_block["description"] or "No description provided."
        wrapped_desc = "\n│ ".join(textwrap.wrap(description, width=70))
        print(desc_box % wrapped_desc)

        # Format and print content
        content = self.current_block["content"] or "No content provided."
        wrapped_content = "\n│ ".join(textwrap.wrap(content, width=70))
        print(content_box % wrapped_content)

        if block_record:
            # Display teaching notes
            speech_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 🗣️ STUDENT SPEECH NOTES                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
            """

            teacher_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ 👨‍🏫 TEACHER NOTES                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
            """

            questions_box = """
┌─────────────────────────────────────────────────────────────────────────┐
│ ❓ STUDENT QUESTIONS                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ %s
└─────────────────────────────────────────────────────────────────────────┘
            """

            # Format and print student speech notes
            speech_notes = (
                block_record["student_speech_notes"] or "No notes recorded yet."
            )
            wrapped_speech = "\n│ ".join(textwrap.wrap(speech_notes, width=70))
            print(speech_box % wrapped_speech)

            # Format and print teacher notes
            teacher_notes = block_record["teacher_notes"] or "No notes recorded yet."
            wrapped_teacher = "\n│ ".join(textwrap.wrap(teacher_notes, width=70))
            print(teacher_box % wrapped_teacher)

            # Format and print student questions
            student_q = (
                block_record["student_questions"] or "No questions recorded yet."
            )
            wrapped_questions = "\n│ ".join(textwrap.wrap(student_q, width=70))
            print(questions_box % wrapped_questions)

        self.print_footer()

    def update_block_notes(
        self, student_speech_notes=None, teacher_notes=None, student_questions=None
    ):
        """Update notes for the current block"""
        if not self.current_block:
            self.print_error("No block selected. Please select a block first.")
            return False

        query = """
        SELECT * FROM block_records
        WHERE lesson_record_id = ? AND block_id = ?
        """
        block_record = self.execute_query(
            query, (self.current_lesson_record["id"], self.current_block["id"]), "one"
        )

        if not block_record:
            self.print_error("Block record not found. Unable to update notes.")
            return False

        # Prepare update fields
        update_parts = []
        params = []

        if student_speech_notes is not None:
            update_parts.append("student_speech_notes = ?")
            params.append(student_speech_notes)

        if teacher_notes is not None:
            update_parts.append("teacher_notes = ?")
            params.append(teacher_notes)

        if student_questions is not None:
            update_parts.append("student_questions = ?")
            params.append(student_questions)

        if not update_parts:
            self.print_error("No updates provided.")
            return False

        # Add modified timestamp
        update_parts.append("modified_at = datetime('now')")

        # Complete the parameters
        params.extend([self.current_lesson_record["id"], self.current_block["id"]])

        query = f"""
        UPDATE block_records
        SET {", ".join(update_parts)}
        WHERE lesson_record_id = ? AND block_id = ?
        """

        self.execute_query(query, params, "commit")
        self.print_success("Notes updated successfully.")
        return True

    def complete_lesson(self, score=None, feedback=None):
        """Mark the current lesson as completed"""
        if not self.current_lesson:
            self.print_error("No lesson selected. Please select a lesson first.")
            return False

        update_parts = ["completion_date = date('now')"]
        params = []

        if score is not None:
            update_parts.append("score = ?")
            params.append(score)

        if feedback is not None:
            update_parts.append("feedback = ?")
            params.append(feedback)

        # Complete the parameters
        params.append(self.current_lesson_record["id"])

        query = f"""
        UPDATE lesson_records
        SET {", ".join(update_parts)}
        WHERE id = ?
        """

        self.execute_query(query, params, "commit")
        self.print_success(
            f"Lesson '{self.current_lesson['title']}' marked as completed."
        )
        return True

    def display_menu(self):
        """Display the main menu with ASCII art icons"""
        print("\n" + "─" * self.terminal_width)
        print(f"{'MAIN MENU':^{self.terminal_width}}")
        print("─" * self.terminal_width)

        menu_items = [
            ("1", "👥 List Students", True),
            ("2", "👤 Select Student", True),
            ("3", "📚 List Units", self.current_student is not None),
            ("4", "📖 Select Unit", self.current_student is not None),
            ("5", "📝 List Lessons", self.current_unit is not None),
            ("6", "📓 Select Lesson", self.current_unit is not None),
            ("7", "📋 Display Lesson Details", self.current_lesson is not None),
            ("8", "🧩 List Blocks", self.current_lesson is not None),
            ("9", "🔍 Select Block", self.current_lesson is not None),
            ("10", "📄 Display Block Details", self.current_block is not None),
            ("11", "🗣️ Update Student Speech Notes", self.current_block is not None),
            ("12", "👨‍🏫 Update Teacher Notes", self.current_block is not None),
            ("13", "❓ Update Student Questions", self.current_block is not None),
            ("14", "✅ Complete Lesson", self.current_lesson is not None),
            ("0", "🚪 Exit", True),
        ]

        # Display menu items with appropriate icons
        for item in menu_items:
            if item[2]:  # Only display if enabled
                print(f"{item[0]}. {item[1]}")

        print("─" * self.terminal_width)

    def run_cli(self):
        """Run the interactive CLI loop"""
        parser = argparse.ArgumentParser(description="ESL Teacher CLI Tool")
        parser.add_argument(
            "--student", type=int, help="ID of the student to work with"
        )
        parser.add_argument("--unit", type=int, help="ID of the unit to work with")
        parser.add_argument("--lesson", type=int, help="ID of the lesson to work with")
        args = parser.parse_args()

        if not self.connect_db():
            self.print_error("Failed to connect to the database. Exiting...")
            sys.exit(1)

        try:
            # Display splash screen
            self.display_splash_screen()
            time.sleep(1)  # Pause for effect

            # Initialize with command line arguments if provided
            if args.student:
                self.select_student(args.student)
                if args.unit:
                    self.select_unit(args.unit)
                    if args.lesson:
                        self.select_lesson(args.lesson)

            while True:
                self.display_menu()
                choice = input("\nEnter your choice: ")

                if choice == "0":
                    break
                elif choice == "1":
                    self.list_students()
                elif choice == "2":
                    student_id = input("Enter student ID: ")
                    self.select_student(int(student_id))
                elif choice == "3" and self.current_student:
                    self.list_units()
                elif choice == "4" and self.current_student:
                    unit_id = input("Enter unit ID: ")
                    self.select_unit(int(unit_id))
                elif choice == "5" and self.current_unit:
                    self.list_lessons()
                elif choice == "6" and self.current_unit:
                    lesson_id = input("Enter lesson ID: ")
                    self.select_lesson(int(lesson_id))
                elif choice == "7" and self.current_lesson:
                    self.display_lesson_details()
                elif choice == "8" and self.current_lesson:
                    self.list_blocks()
                elif choice == "9" and self.current_lesson:
                    block_id = input("Enter block ID: ")
                    self.select_block(int(block_id))
                elif choice == "10" and self.current_block:
                    self.display_block_details()
                elif choice == "11" and self.current_block:
                    notes = input(
                        "Enter student speech notes (or press Enter to keep current): "
                    )
                    if notes.strip():
                        self.update_block_notes(student_speech_notes=notes)
                elif choice == "12" and self.current_block:
                    notes = input(
                        "Enter teacher notes (or press Enter to keep current): "
                    )
                    if notes.strip():
                        self.update_block_notes(teacher_notes=notes)
                elif choice == "13" and self.current_block:
                    questions = input(
                        "Enter student questions (or press Enter to keep current): "
                    )
                    if questions.strip():
                        self.update_block_notes(student_questions=questions)
                elif choice == "14" and self.current_lesson:
                    score = input("Enter score (0-100, or press Enter to skip): ")
                    score = int(score) if score.strip() and score.isdigit() else None
                    feedback = input("Enter feedback (or press Enter to skip): ")
                    feedback = feedback if feedback.strip() else None
                    self.complete_lesson(score, feedback)
                else:
                    self.print_error("Invalid choice. Please try again.")

                # Pause to allow user to read output
                input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print("\nExiting ESL Teacher CLI...")
        except Exception as e:
            self.print_error(f"An error occurred: {e}")
        finally:
            self.close_db()
            print("\nGoodbye!")


if __name__ == "__main__":
    cli = ESLTeacherCLI()
    cli.run_cli()
