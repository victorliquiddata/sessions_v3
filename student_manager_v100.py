from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import sqlite3
import os
import sys
from datetime import datetime
import textwrap
import re
import logging
import time

# Configure logging
logging.basicConfig(filename="student_manager.log", level=logging.ERROR)

# Initialize Rich console
console = Console()

# Define color schemes (matching esl_teacher_cli_v1_22.py)
COLOR_SCHEMES = {
    "default": {
        "primary": "cyan",
        "secondary": "bright_white",
        "error": "red",
        "success": "green",
        "warning": "yellow",
        "info": "blue",
        "highlight": "magenta",
    },
    "blue_background": {
        "primary": "bright_black",
        "secondary": "white",
        "error": "red",
        "success": "green",
        "warning": "yellow",
        "info": "blue",
        "highlight": "magenta",
    },
}
# Define MENU_OPTIONS
MENU_OPTIONS = {
    "1": "List All Students",
    "2": "Add New Student",
    "3": "Update Student Information",
    "4": "Remove Student",
    "5": "View Student Progress",
    "6": "Record Lesson Completion",
    "7": "List Available Courses",
    "8": "List Students by Course",
    "9": "Help",
    "0": "Exit",
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


class StudentManager:
    def __init__(self, db_path="esl.db", theme="default"):
        """
        Initialize the StudentManager with a database connection and Rich console.

        Args:
            db_path (str, optional): Path to the SQLite database. Defaults to "esl.db".
            theme (str, optional): Theme to use for styling (e.g., "default" or "blue_background"). Defaults to "default".
        """
        self.db_path = db_path
        self.theme = theme  # Store the selected theme
        self.conn = None
        self.cursor = None
        self.console = Console()  # Initialize the Rich console

        try:
            self.connect_db()
            self.console.print(
                f"✅ Connected to database: {db_path}",
                style=COLOR_SCHEMES[self.theme]["success"],  # Use the selected theme
            )
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            self.console.print(
                f"❌ Database error: {e}",
                style=COLOR_SCHEMES[self.theme]["error"],  # Use the selected theme
            )
            sys.exit(1)

    def connect_db(self):
        """Connect to the SQLite database."""
        if not os.path.exists(self.db_path):
            console.print(
                f"❌ Database file {self.db_path} does not exist!",
                style=COLOR_SCHEMES["error"],
            )
            sys.exit(1)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def close_db(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            console.print("👋 Database connection closed", style=COLOR_SCHEMES["info"])

    def validate_email(self, email):
        """Validate email format using regex."""
        if not email:
            return False
        pattern = (
            r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$"
        )
        return re.match(pattern, email) is not None

    def validate_name(self, name):
        """Validate name format using regex."""
        if not name:
            return False
        return all(c.isalpha() or c.isspace() or c in "-'." for c in name)

    def validate_integer(self, value, min_val=1, max_val=None):
        """Validate integer input."""
        try:
            val = int(value)
            if val < min_val:
                return False
            if max_val and val > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False

    def validate_score(self, score):
        """Validate score input (0-100 or None)."""
        if score is None or score == "":
            return True, None
        try:
            score_val = int(score)
            if 0 <= score_val <= 100:
                return True, score_val
            return False, None
        except (ValueError, TypeError):
            return False, None

    def check_student_exists(self, student_id):
        """Check if a student exists by ID."""
        self.cursor.execute(
            "SELECT id FROM enrolled_students WHERE id = ?", (student_id,)
        )
        return self.cursor.fetchone() is not None

    def check_course_exists(self, course_id):
        """Check if a course exists by ID."""
        self.cursor.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
        return self.cursor.fetchone() is not None

    def check_lesson_exists(self, lesson_id):
        """Check if a lesson exists by ID."""
        self.cursor.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,))
        return self.cursor.fetchone() is not None

    def add_student(self, name, email, course_id):
        """Add a new student to the enrolled_students table."""
        try:
            # Validate inputs
            if not self.validate_name(name):
                return "❌ Invalid name. Name must be at least 2 characters long."
            if not self.validate_email(email):
                return "❌ Invalid email format."
            if not self.validate_integer(course_id):
                return "❌ Invalid course ID."

            # Check if email already exists
            self.cursor.execute(
                "SELECT id FROM enrolled_students WHERE email = ?", (email,)
            )
            if self.cursor.fetchone():
                return f"❌ Student with email {email} already exists."

            # Insert new student
            today = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                "INSERT INTO enrolled_students (name, email, enrollment_date, course_id) VALUES (?, ?, ?, ?)",
                (name, email, today, course_id),
            )
            self.conn.commit()
            return f"✅ Student {name} added successfully!"
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error adding student: {e}")
            return f"❌ Error: {e}"

    def remove_student(self, student_id):
        """Remove a student from the enrolled_students table."""
        try:
            # First delete related records
            self.cursor.execute(
                "DELETE FROM lesson_records WHERE student_id = ?", (student_id,)
            )

            # Then delete the student
            self.cursor.execute(
                "DELETE FROM enrolled_students WHERE id = ?", (student_id,)
            )
            self.conn.commit()
            return f"✅ Student (ID: {student_id}) removed successfully!"
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error removing student: {e}")
            return f"❌ Error: {e}"

    def update_student(self, student_id, name=None, email=None, course_id=None):
        """Update student information."""
        try:
            # Validate student_id
            if not self.check_student_exists(student_id):
                return f"❌ Student with ID {student_id} does not exist."

            # Prepare updates
            updates = []
            params = []
            if name:
                if not self.validate_name(name):
                    return "❌ Invalid name. Name must be at least 2 characters long."
                updates.append("name = ?")
                params.append(name)
            if email:
                if not self.validate_email(email):
                    return "❌ Invalid email format."
                updates.append("email = ?")
                params.append(email)
            if course_id:
                if not self.validate_integer(course_id):
                    return "❌ Invalid course ID."
                updates.append("course_id = ?")
                params.append(course_id)

            if not updates:
                return "❌ No updates provided."

            # Build and execute the query
            query = f"UPDATE enrolled_students SET {', '.join(updates)} WHERE id = ?"
            params.append(student_id)
            self.cursor.execute(query, params)
            self.conn.commit()
            return f"✅ Student {student_id} updated successfully!"
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error updating student: {e}")
            return f"❌ Error: {e}"

    def list_students(self, course_id=None, theme="default"):
        """
        List all students, optionally filtered by course_id.

        Args:
            course_id (int, optional): The ID of the course to filter students by. Defaults to None.
            theme (str, optional): The theme to use for styling (e.g., "default" or "blue_background"). Defaults to "default".

        Returns:
            Union[Table, str]: A Rich Table object if students are found, otherwise a string message.
        """
        try:
            if course_id:
                self.cursor.execute(
                    """
                    SELECT s.id, s.name, s.email, s.enrollment_date, c.name as course_name
                    FROM enrolled_students s
                    JOIN courses c ON s.course_id = c.id
                    WHERE s.course_id = ?
                    ORDER BY s.name
                    """,
                    (course_id,),
                )
            else:
                self.cursor.execute(
                    """
                    SELECT s.id, s.name, s.email, s.enrollment_date, c.name as course_name
                    FROM enrolled_students s
                    JOIN courses c ON s.course_id = c.id
                    ORDER BY s.name
                    """
                )

            students = self.cursor.fetchall()
            if not students:
                return "📝 No students found"

            # Create Rich table
            table = Table(
                title="Student List",
                border_style=COLOR_SCHEMES[theme]["primary"],  # Use the selected theme
            )
            table.add_column(
                "ID", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
            )
            table.add_column("Name", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column("Email", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column("Enrollment Date", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column("Course", style=COLOR_SCHEMES[theme]["secondary"])

            for s in students:
                table.add_row(
                    str(s["id"]),
                    s["name"],
                    s["email"],
                    s["enrollment_date"],
                    s["course_name"],
                )

            return table
        except sqlite3.Error as e:
            logging.error(f"Error listing students: {e}")
            return f"❌ Error: {e}"

    def get_student_progress(self, student_id, theme="default"):
        """
        Get progress information for a specific student.

        Args:
            student_id (int): The ID of the student.
            theme (str, optional): The theme to use for styling (e.g., "default" or "blue_background"). Defaults to "default".

        Returns:
            Union[Panel, str]: A Rich Panel object if progress data is found, otherwise a string message.
        """
        try:
            # First check if student exists
            self.cursor.execute(
                "SELECT name FROM enrolled_students WHERE id = ?", (student_id,)
            )
            student = self.cursor.fetchone()
            if not student:
                return f"❌ Student with ID {student_id} does not exist"

            # Get student's course information
            self.cursor.execute(
                """
                SELECT c.name as course_name, c.id as course_id
                FROM enrolled_students s
                JOIN courses c ON s.course_id = c.id
                WHERE s.id = ?
                """,
                (student_id,),
            )
            course = self.cursor.fetchone()

            # Get completed lessons
            self.cursor.execute(
                """
                SELECT lr.id, l.id as lesson_id, l.title, u.title as unit_title, u.unit_number, lr.completion_date, lr.score, lr.feedback
                FROM lesson_records lr
                JOIN lessons l ON lr.lesson_id = l.id
                JOIN units u ON l.unit_id = u.id
                WHERE lr.student_id = ?
                ORDER BY lr.completion_date DESC
                """,
                (student_id,),
            )
            lessons = self.cursor.fetchall()

            # Get total lessons in student's course
            self.cursor.execute(
                """
                SELECT COUNT(*) as total_lessons
                FROM lessons l
                JOIN units u ON l.unit_id = u.id
                WHERE u.course_id = ?
                """,
                (course["course_id"],),
            )
            total_lessons = self.cursor.fetchone()["total_lessons"]

            # Build Rich report
            report = Panel(
                Text.from_markup(
                    f"📊 Progress Report for: {student['name']}\n"
                    f"🎓 Course: {course['course_name']}\n"
                    f"✅ Completed Lessons: {len(lessons)} of {total_lessons} ({int(len(lessons) / total_lessons * 100 if total_lessons else 0)}%)\n"
                ),
                title="Student Progress",
                border_style=COLOR_SCHEMES[theme]["success"],  # Use the selected theme
            )

            if lessons:
                # Calculate average score if there are scores available
                scores = [l["score"] for l in lessons if l["score"] is not None]
                avg_score = sum(scores) / len(scores) if scores else None

                if avg_score is not None:
                    report = Panel(
                        Text.from_markup(
                            f"📊 Progress Report for: {student['name']}\n"
                            f"🎓 Course: {course['course_name']}\n"
                            f"✅ Completed Lessons: {len(lessons)} of {total_lessons} ({int(len(lessons) / total_lessons * 100 if total_lessons else 0)}%)\n"
                            f"📈 Average Score: {avg_score:.1f}%\n"
                        ),
                        title="Student Progress",
                        border_style=COLOR_SCHEMES[theme][
                            "success"
                        ],  # Use the selected theme
                    )

                # Create table for completed lessons
                lesson_table = Table(
                    title="Recent Lesson Progress",
                    border_style=COLOR_SCHEMES[theme][
                        "primary"
                    ],  # Use the selected theme
                )
                lesson_table.add_column(
                    "Lesson ID",
                    style=COLOR_SCHEMES[theme]["secondary"],
                    justify="right",
                )  # New column
                lesson_table.add_column(
                    "Unit #", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
                )
                lesson_table.add_column(
                    "Lesson", style=COLOR_SCHEMES[theme]["secondary"]
                )
                lesson_table.add_column("Unit", style=COLOR_SCHEMES[theme]["secondary"])
                lesson_table.add_column("Date", style=COLOR_SCHEMES[theme]["secondary"])
                lesson_table.add_column(
                    "Score", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
                )
                lesson_table.add_column(
                    "Feedback", style=COLOR_SCHEMES[theme]["secondary"]
                )

                for l in lessons[:5]:  # Show only the 5 most recent
                    lesson_table.add_row(
                        str(l["lesson_id"]),  # Add lesson ID
                        str(l["unit_number"]),  # Add unit number
                        l["title"],
                        l["unit_title"],
                        l["completion_date"],
                        f"{l['score']}%" if l["score"] is not None else "N/A",
                        textwrap.shorten(l["feedback"] or "No feedback", width=30),
                    )

                # Print the report and table
                self.console.print(report)
                self.console.print(lesson_table)
            else:
                # Print a warning panel if no lessons are found
                self.console.print(
                    Panel(
                        "❗ No completed lessons found",
                        border_style=COLOR_SCHEMES[theme][
                            "warning"
                        ],  # Use the selected theme
                    )
                )

            return report
        except sqlite3.Error as e:
            logging.error(f"Error getting student progress: {e}")
            return f"❌ Error: {e}"

    def record_lesson_completion(
        self, student_id, lesson_id, score=None, feedback=None
    ):
        """Record the completion of a lesson by a student."""
        try:
            # Validate inputs
            if not self.check_student_exists(student_id):
                return f"❌ Student with ID {student_id} does not exist."
            if not self.check_lesson_exists(lesson_id):
                return f"❌ Lesson with ID {lesson_id} does not exist."
            if score is not None and not self.validate_score(score):
                return "❌ Invalid score. Score must be between 0 and 100."

            # Insert or update lesson record
            self.cursor.execute(
                """
                INSERT INTO lesson_records (student_id, lesson_id, score, feedback, completion_date)
                VALUES (?, ?, ?, ?, date('now'))
                ON CONFLICT(student_id, lesson_id) DO UPDATE SET
                    score = excluded.score,
                    feedback = excluded.feedback,
                    completion_date = excluded.completion_date
                """,
                (student_id, lesson_id, score, feedback),
            )
            self.conn.commit()
            return f"✅ Lesson {lesson_id} recorded for student {student_id}."
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error recording lesson completion: {e}")
            return f"❌ Error: {e}"

    def list_available_courses(self, theme="default"):
        """
        List all available courses in the database.

        Args:
            theme (str, optional): The theme to use for styling (e.g., "default" or "blue_background"). Defaults to "default".

        Returns:
            Union[Table, str]: A Rich Table object if courses are found, otherwise a string message.
        """
        try:
            self.cursor.execute(
                """
                SELECT c.id, c.name, c.focus, c.duration, 
                    (SELECT COUNT(*) FROM units WHERE course_id = c.id) as unit_count,
                    (SELECT COUNT(*) FROM enrolled_students WHERE course_id = c.id) as student_count
                FROM courses c
                ORDER BY c.name
                """
            )
            courses = self.cursor.fetchall()

            if not courses:
                return "📚 No courses available"

            # Create Rich table
            table = Table(
                title="Available Courses",
                border_style=COLOR_SCHEMES[theme]["primary"],  # Use the selected theme
            )
            table.add_column(
                "ID", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
            )
            table.add_column("Course Name", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column("Focus", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column("Duration", style=COLOR_SCHEMES[theme]["secondary"])
            table.add_column(
                "Units", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
            )
            table.add_column(
                "Students", style=COLOR_SCHEMES[theme]["secondary"], justify="right"
            )

            for c in courses:
                table.add_row(
                    str(c["id"]),
                    c["name"],
                    c["focus"] or "N/A",  # Handle null values
                    c["duration"] or "N/A",  # Handle null values
                    str(c["unit_count"]),
                    str(c["student_count"]),
                )

            return table
        except sqlite3.Error as e:
            logging.error(f"Error listing courses: {e}")
            return f"❌ Error: {e}"

    def list_lessons_for_course(self, course_id):
        """List all lessons for a specific course."""
        try:
            self.cursor.execute(
                """
                SELECT l.id, l.title, u.title as unit_title
                FROM lessons l
                JOIN units u ON l.unit_id = u.id
                WHERE u.course_id = ?
                ORDER BY u.unit_number, l.lesson_number
                """,
                (course_id,),
            )
            lessons = self.cursor.fetchall()

            if not lessons:
                return "📝 No lessons found for this course"

            # Create Rich table
            table = Table(title="Lessons", border_style=COLOR_SCHEMES["primary"])
            table.add_column("ID", style=COLOR_SCHEMES["secondary"], justify="right")
            table.add_column("Lesson Title", style=COLOR_SCHEMES["secondary"])
            table.add_column("Unit", style=COLOR_SCHEMES["secondary"])

            for l in lessons:
                table.add_row(str(l["id"]), l["title"], l["unit_title"])

            return table
        except sqlite3.Error as e:
            logging.error(f"Error listing lessons: {e}")
            return f"❌ Error: {e}"

    def get_valid_input(self, prompt, validation_func, error_message, *validation_args):
        """
        Get valid input from the user.

        Args:
            prompt (str): The input prompt to display.
            validation_func (callable): The validation function to use.
            error_message (str): The error message to display if validation fails.
            *validation_args: Additional arguments to pass to the validation function.

        Returns:
            The validated input.
        """
        while True:
            user_input = self.console.input(prompt).strip()
            if validation_func(user_input, *validation_args):
                return user_input
            self.console.print(error_message, style=COLOR_SCHEMES[self.theme]["error"])


def get_input(prompt, validator=None, error_msg=None, required=True):
    """
    Get and validate user input with immediate feedback.

    Args:
        prompt: The input prompt to display
        validator: Optional validation function to call
        error_msg: Custom error message for validation failures
        required: Whether the field is required

    Returns:
        The validated input value
    """
    while True:
        value = input(prompt).strip()

        # Check if required
        if not value:
            if not required:
                return value
            print("❌ This field is required!")
            continue

        # Validate if validator provided
        if validator and not validator(value):
            print(error_msg or "❌ Invalid input!")
            continue

        return value


def get_numeric_input(prompt, min_val=1, max_val=None, required=True):
    """Get and validate numeric input."""
    while True:
        value = input(prompt).strip()

        # Handle optional input
        if not required and not value:
            return None

        # Validate numeric input
        try:
            num = int(value)
            if num < min_val:
                print(f"❌ Value must be at least {min_val}!")
                continue

            if max_val and num > max_val:
                print(f"❌ Value must be no more than {max_val}!")
                continue

            return num
        except ValueError:
            print("❌ Please enter a valid number!")


def get_student_id(manager, prompt="🔢 Student ID: "):
    """Get and validate student ID."""
    while True:
        student_id = get_numeric_input(prompt)
        if manager.check_student_exists(student_id):
            return student_id
        print(f"❌ Student with ID {student_id} does not exist")


def get_course_id(manager, prompt="🔢 Course ID: "):
    """Get and validate course ID."""
    while True:
        course_id = get_numeric_input(prompt)
        if manager.check_course_exists(course_id):
            return course_id
        print(f"❌ Course with ID {course_id} does not exist")


def get_lesson_id(manager, prompt="🔢 Lesson ID: "):
    """Get and validate lesson ID."""
    while True:
        lesson_id = get_numeric_input(prompt)
        if manager.check_lesson_exists(lesson_id):
            return lesson_id
        print(f"❌ Lesson with ID {lesson_id} does not exist")


def get_score_input(manager, prompt="📊 Score (0-100, optional): "):
    """Get and validate score input."""
    while True:
        score_input = input(prompt).strip()
        if not score_input:
            return None

        is_valid, score = manager.validate_score(score_input)
        if is_valid:
            return score
        print("❌ Score must be a number between 0 and 100")


def print_help():
    """Display help information."""
    help_text = """
    🌟 ESL Student Manager Help 🌟

    1️⃣  List All Students: View all enrolled students.
    2️⃣  Add New Student: Add a new student to the database.
    3️⃣  Update Student Information: Update a student's details.
    4️⃣  Remove Student: Remove a student from the database.
    5️⃣  View Student Progress: View a student's progress and completed lessons.
    6️⃣  Record Lesson Completion: Record a student's completion of a lesson.
    7️⃣  List Available Courses: View all available courses.
    8️⃣  List Students by Course: View students enrolled in a specific course.
    9️⃣  Help: Display this help information.
    0️⃣  Exit: Exit the application.
    """
    print(help_text)
    input("\nPress Enter to continue...")


def print_menu():
    """Print the main menu options."""
    clear_screen()
    menu = "\n🌟 ESL Student Manager 🌟\n"
    for key, value in MENU_OPTIONS.items():
        menu += f"\n{key}️⃣  {value}"
    menu += "\n\n👉 Choose an option: "
    return input(menu)


def main():
    """Main function to run the student manager program."""
    manager = StudentManager()

    while True:
        choice = print_menu()

        if choice == "1":
            # List all students
            print("\n📋 Student List:")
            print(manager.list_students())
            input("\nPress Enter to continue...")

        elif choice == "2":
            # Add new student with immediate validation
            print("\n➕ Add New Student:")

            # Validate name immediately
            name = get_input(
                "👤 Name: ",
                validator=manager.validate_name,
                error_msg="❌ Invalid name. Please use only letters, spaces, hyphens, apostrophes, and periods.",
            )

            # Validate email immediately
            email = get_input(
                "📧 Email: ",
                validator=manager.validate_email,
                error_msg="❌ Invalid email format. Please use a valid email address (e.g., user@example.com)",
            )

            # Show available courses
            print("\nAvailable Courses:")
            print(manager.list_available_courses())

            # Validate course ID immediately
            course_id = get_course_id(manager)

            result = manager.add_student(name, email, course_id)
            print(f"\n{result}")
            input("\nPress Enter to continue...")

        elif choice == "3":
            # Update student with immediate validation
            print("\n✏️ Update Student:")
            print(manager.list_students())

            # Validate student ID immediately
            student_id = get_student_id(manager, "🔢 Student ID to update: ")

            print("Leave blank to keep current value")

            # Validate name (if provided)
            name = get_input(
                "👤 New name (optional): ",
                validator=lambda x: not x or manager.validate_name(x),
                error_msg="❌ Invalid name. Please use only letters, spaces, hyphens, apostrophes, and periods.",
                required=False,
            )

            # Validate email (if provided)
            email = get_input(
                "📧 New email (optional): ",
                validator=lambda x: not x or manager.validate_email(x),
                error_msg="❌ Invalid email format. Please use a valid email address (e.g., user@example.com)",
                required=False,
            )

            change_course = get_input("Change course? (y/n): ").lower() == "y"
            course_id = None
            if change_course:
                print(manager.list_available_courses())
                course_id = get_course_id(manager, "🔢 New course ID: ")

            result = manager.update_student(student_id, name, email, course_id)
            print(f"\n{result}")
            input("\nPress Enter to continue...")

        elif choice == "4":
            # Remove student with immediate validation
            print("\n❌ Remove Student:")
            print(manager.list_students())

            # Validate student ID immediately
            student_id = get_student_id(manager, "🔢 Student ID to remove: ")

            confirm = get_input(
                f"⚠️ Are you sure you want to remove student {student_id}? (y/n): "
            )
            if confirm.lower() == "y":
                result = manager.remove_student(student_id)
                print(f"\n{result}")
            else:
                print("🛑 Removal cancelled")
            input("\nPress Enter to continue...")

        elif choice == "5":
            # View student progress with immediate validation
            print("\n📊 View Student Progress:")
            print(manager.list_students())

            # Validate student ID immediately
            student_id = get_student_id(manager)

            progress = manager.get_student_progress(student_id)
            print(f"\n{progress}")
            input("\nPress Enter to continue...")

        elif choice == "6":
            # Record lesson completion with immediate validation
            print("\n✅ Record Lesson Completion:")
            print(manager.list_students())

            # Validate student ID immediately
            student_id = get_student_id(manager)

            # Get course for student
            manager.cursor.execute(
                "SELECT course_id FROM enrolled_students WHERE id = ?", (student_id,)
            )
            student = manager.cursor.fetchone()
            course_id = student["course_id"]

            # List lessons for the student's course
            print(f"\nLessons for this student's course:")
            print(manager.list_lessons_for_course(course_id))

            # Validate lesson ID immediately
            lesson_id = get_lesson_id(manager)

            # Validate score immediately
            score = get_score_input(manager)

            # Get feedback
            feedback = get_input("💬 Feedback (optional): ", required=False)

            result = manager.record_lesson_completion(
                student_id, lesson_id, score, feedback
            )
            print(f"\n{result}")
            input("\nPress Enter to continue...")

        elif choice == "7":
            # List available courses
            print("\n📚 Available Courses:")
            print(manager.list_available_courses())
            input("\nPress Enter to continue...")

        elif choice == "8":
            # List students by course with immediate validation
            print("\n🎓 List Students by Course:")
            print(manager.list_available_courses())

            # Validate course ID immediately
            course_id = get_course_id(manager)

            print(f"\n📋 Students in Course {course_id}:")
            print(manager.list_students(course_id))
            input("\nPress Enter to continue...")

        elif choice == "9":
            # Display help
            print_help()

        elif choice == "0":
            # Exit
            manager.close_db()
            print("\n👋 Thank you for using ESL Student Manager! Goodbye!")
            break

        else:
            print("\n❌ Invalid option. Please try again.")
            time.sleep(1)


if __name__ == "__main__":
    main()
