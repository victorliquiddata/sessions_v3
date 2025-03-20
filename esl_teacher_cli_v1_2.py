"This code is a ESL Teacher Assistant"

import google.generativeai as genai
import os
from dotenv import load_dotenv
import webbrowser
import urllib.parse
import sys
import sqlite3
import argparse
import time
import shutil
from prompt_toolkit import prompt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.box import ROUNDED, DOUBLE, HEAVY


class ESLTeacherCLI:
    """Handles all ops"""

    # Add this template as a class-level constant
    TEACHER_NOTES_TEMPLATE = """
    Lesson Overview:
    Topic: {lesson_topic}
    Student: {student_name}
    Level: {student_level}

    Block: {block_title} (Activity: {block_activity_type})
    Content: Provide teaching notes for {block_title} related to {lesson_topic} for a {student_level} student.
    Don't use asterisks, keep only text and dashes for bullet points, and keep character amount with spaces between 200 to 300.
    Teacher-Student Interaction:
    [Teacher]: [concise "Your message"]
    [Student]: [concise "Expected response"]
    """

    def __init__(
        self,
        db_path="esl.db",
    ):
        """Initialize the CLI with database connection"""
        self.db_path = db_path  # Use the full path to the database
        self.connection = None
        self.cursor = None
        self.current_student = None
        self.current_course = None
        self.current_unit = None
        self.current_lesson = None
        self.current_block = None
        self.current_lesson_record = None

        # Set up rich console
        self.console = Console()

        # Get terminal size for better UI formatting
        self.terminal_width, self.terminal_height = shutil.get_terminal_size()

        # Search-related constants
        self.SEARCH_URLS = {
            "Google Search": "https://www.google.com/search?q=",
            "Google Images": "https://www.google.com/search?tbm=isch&q=",
            "Google News": "https://www.google.com/search?tbm=nws&q=",
        }
        self.ASSETS_DIR = "./assets"  # Change this path if needed

    def connect_db(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(
                self.db_path
            )  # Connect using the full path
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

    def get_block_details(self, block_id):
        """Fetch block details from the database."""
        query = """
        SELECT title, activity_type
        FROM blocks
        WHERE id = ?
        """
        block_details = self.execute_query(query, (block_id,), "one")
        return block_details

    def prepare_gemini_prompt(self):
        """Prepare the prompt for Gemini using the template and current context."""
        if (
            not self.current_block
            or not self.current_lesson
            or not self.current_student
        ):
            self.print_error(
                "No block, lesson, or student selected. Please select a block first."
            )
            return None

        # Fetch block details
        block_details = self.get_block_details(self.current_block["id"])
        if not block_details:
            self.print_error("Block details not found.")
            return None

        # Fetch additional details if needed
        student_level = self.current_student.get(
            "level", "Unknown Level"
        )  # Assuming 'level' is stored in the student record
        lesson_topic = self.current_lesson["title"]
        block_title = block_details["title"]
        block_number = self.current_block["block_number"]
        block_id = self.current_block["id"]
        block_activity_type = block_details["activity_type"]

        # Populate the template
        prompt = self.TEACHER_NOTES_TEMPLATE.format(
            lesson_topic=lesson_topic,
            student_name=self.current_student["name"],
            student_level=student_level,
            block_title=block_title,
            block_number=block_number,
            block_id=block_id,
            block_activity_type=block_activity_type,
        )

        return prompt

    def generate_teacher_notes_with_gemini(self):
        """Generate teacher notes using Gemini AI."""
        if not self.current_block:
            self.print_error("No block selected. Please select a block first.")
            return

        # Setup Gemini API
        if not self.setup_gemini_api():
            input("\nPress Enter to return to block details...")
            return

        try:
            # Prepare the prompt
            prompt = self.prepare_gemini_prompt()
            if not prompt:
                return

            # Initialize the model
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Generate the response
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Generating teacher notes...", total=None
                )
                response = model.generate_content(prompt)

            # Display the generated notes
            self.console.print(
                Panel(
                    response.text,
                    box=ROUNDED,
                    border_style="green",
                    title="Generated Teacher Notes",
                )
            )

            # Ask if the user wants to save the generated notes
            save_choice = (
                input("\nDo you want to save these notes? (y/n): ").strip().lower()
            )
            if save_choice == "y":
                self.update_block_notes(teacher_notes=response.text)
                self.print_success("Teacher notes saved successfully.")
            else:
                self.print_success("Teacher notes were not saved.")

        except Exception as e:
            self.print_error(f"Error generating teacher notes: {str(e)}")

        input("\nPress Enter to continue...")  # Pause for user to read output

    def setup_gemini_api(self):
        """Setup the Gemini API with your key"""
        load_dotenv()  # Load API key from .env file
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.print_error("GOOGLE_API_KEY not found in environment variables.")
            return False
        try:
            genai.configure(api_key=api_key)
            return True
        except Exception as e:
            self.print_error(f"Error setting up Gemini API: {str(e)}")
            return False

    def get_current_context(self):
        """Get context information based on what's currently selected"""
        context_parts = []

        # Add student context if selected
        if self.current_student:
            student_info = self.execute_query(
                "SELECT name, email, enrollment_date FROM enrolled_students WHERE id = ?",
                (self.current_student["id"],),
                "one",
            )
            if student_info:
                context_parts.append(f"Student: {student_info['name']}")
                context_parts.append(f"Email: {student_info['email']}")
                context_parts.append(
                    f"Enrollment Date: {student_info['enrollment_date']}"
                )

        # Add course context if selected
        if self.current_course:
            course_info = self.execute_query(
                "SELECT name, focus, themes, grammar_overview, vocabulary_overview FROM courses WHERE id = ?",
                (self.current_course["id"],),
                "one",
            )
            if course_info:
                context_parts.append(f"Course: {course_info['name']}")
                if course_info["focus"]:
                    context_parts.append(f"Focus: {course_info['focus']}")
                if course_info["themes"]:
                    context_parts.append(f"Themes: {course_info['themes']}")
                if course_info["grammar_overview"]:
                    context_parts.append(
                        f"Grammar Overview: {course_info['grammar_overview']}"
                    )
                if course_info["vocabulary_overview"]:
                    context_parts.append(
                        f"Vocabulary Overview: {course_info['vocabulary_overview']}"
                    )

        # Add unit context if selected
        if self.current_unit:
            unit_info = self.execute_query(
                "SELECT unit_number, title, description FROM units WHERE id = ?",
                (self.current_unit["id"],),
                "one",
            )
            if unit_info:
                context_parts.append(
                    f"Unit: {unit_info['unit_number']} - {unit_info['title']}"
                )
                if unit_info["description"]:
                    context_parts.append(f"Description: {unit_info['description']}")

        # Add lesson context if selected
        if self.current_lesson:
            lesson_info = self.execute_query(
                "SELECT lesson_number, title, context, grammar_focus, vocabulary_focus FROM lessons WHERE id = ?",
                (self.current_lesson["id"],),
                "one",
            )
            if lesson_info:
                context_parts.append(
                    f"Lesson: {lesson_info['lesson_number']} - {lesson_info['title']}"
                )
                if lesson_info["context"]:
                    context_parts.append(f"Context: {lesson_info['context']}")
                if lesson_info["grammar_focus"]:
                    context_parts.append(
                        f"Grammar Focus: {lesson_info['grammar_focus']}"
                    )
                if lesson_info["vocabulary_focus"]:
                    context_parts.append(
                        f"Vocabulary Focus: {lesson_info['vocabulary_focus']}"
                    )

        # Add block context if selected
        if self.current_block:
            block_info = self.execute_query(
                "SELECT block_number, title, description, activity_type, content FROM blocks WHERE id = ?",
                (self.current_block["id"],),
                "one",
            )
            if block_info:
                context_parts.append(
                    f"Block: {block_info['block_number']} - {block_info['title']}"
                )
                if block_info["description"]:
                    context_parts.append(f"Description: {block_info['description']}")
                if block_info["activity_type"]:
                    context_parts.append(
                        f"Activity Type: {block_info['activity_type']}"
                    )
                if block_info["content"]:
                    context_parts.append(f"Content: {block_info['content']}")

        return "\n".join(context_parts) if context_parts else "No context available."

    def google_search(self, search_type):
        """Perform a Google Search based on the selected type."""
        query = prompt(f"Enter {search_type} query: ")
        if query.strip():
            search_url = self.SEARCH_URLS[search_type] + urllib.parse.quote(query)
            webbrowser.open(search_url)
            self.print_success(f"Opened {search_type} for: {query}")

    def search_local_assets(self):
        """Search for a file inside the '/assets' directory."""
        query = prompt("Enter filename (or part of it) to search in /assets: ").lower()
        if not os.path.exists(self.ASSETS_DIR):
            self.print_error("The /assets directory does not exist!")
            return

        matches = [f for f in os.listdir(self.ASSETS_DIR) if query in f.lower()]

        if matches:
            self.console.print("\n📂 Found files:", style="bold green")
            for match in matches:
                self.console.print(f" - {match}", style="bright_white")
        else:
            self.print_error("No matching files found.")

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
        """Print a formatted header with breadcrumb navigation"""
        self.clear_screen()

        # Create a rich panel for the header
        header_text = Text()
        header_text.append("ESL TEACHER ASSISTANT\n", style="bold cyan")
        header_text.append(title, style="bold white")

        header_panel = Panel(
            header_text,
            box=DOUBLE,
            border_style="bright_blue",
            expand=True,
            padding=(1, 2),
        )

        self.console.print(header_panel)

        # Add breadcrumb navigation
        self.print_breadcrumbs()

    def print_footer(self):
        """Print a formatted footer"""
        footer_parts = []
        if self.current_student:
            footer_parts.append(f"[bold]Student:[/bold] {self.current_student['name']}")
        if self.current_course:
            footer_parts.append(f"[bold]Course:[/bold] {self.current_course['name']}")
        if self.current_unit:
            footer_parts.append(
                f"[bold]Unit:[/bold] {self.current_unit['unit_number']}"
            )
        if self.current_lesson:
            footer_parts.append(
                f"[bold]Lesson:[/bold] {self.current_lesson['lesson_number']}"
            )

        if footer_parts:
            footer_text = " | ".join(footer_parts)
            footer_panel = Panel(
                footer_text,
                box=ROUNDED,
                border_style="bright_blue",
                expand=True,
                padding=(1, 2),
            )
            self.console.print(footer_panel)

    def print_error(self, message):
        """Print error message with formatting"""
        error_panel = Panel(
            f"{message}",
            title="ERROR",
            title_align="left",
            border_style="red",
            box=HEAVY,
            padding=(1, 2),
        )
        self.console.print(error_panel)

    def print_success(self, message):
        """Print success message with formatting"""
        success_panel = Panel(
            f"{message}",
            title="SUCCESS",
            title_align="left",
            border_style="green",
            box=HEAVY,
            padding=(1, 2),
        )
        self.console.print(success_panel)

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

        splash_panel = Panel(
            Text(splash, style="bright_cyan", justify="center"),
            box=ROUNDED,
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print(splash_panel)

        # Centered text below splash
        # Corrected code
        self.console.print(
            "Your Digital Teaching Companion", style="bold cyan", justify="center"
        )
        self.console.print(
            "Version 1.1.0 By Victor Didier 🤓", style="cyan", justify="center"
        )

        # Animated loading bar with rich
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Loading...[/cyan]"),
            BarColumn(
                bar_width=None, complete_style="cyan", finished_style="bright_cyan"
            ),
            expand=True,
        ) as progress:
            task = progress.add_task("[cyan]Starting up...", total=100)

            for i in range(101):
                progress.update(task, completed=i)
                time.sleep(0.02)

    def print_breadcrumbs(self):
        """Print breadcrumb navigation showing the current path"""
        breadcrumb_parts = []

        # Always start with Home
        breadcrumb_parts.append(("[bold cyan]Home[/bold cyan]", None))

        # Add subsequent levels based on what's selected
        if self.current_student:
            breadcrumb_parts.append((" > ", None))
            breadcrumb_parts.append(
                (
                    f"[bold cyan]Student:[/bold cyan] {self.current_student['name']}",
                    "student",
                )
            )

        if self.current_course:
            breadcrumb_parts.append((" > ", None))
            breadcrumb_parts.append(
                (
                    f"[bold cyan]Course:[/bold cyan] {self.current_course['name']}",
                    "course",
                )
            )

        if self.current_unit:
            breadcrumb_parts.append((" > ", None))
            breadcrumb_parts.append(
                (
                    f"[bold cyan]Unit:[/bold cyan] {self.current_unit['unit_number']}: {self.current_unit['title']}",
                    "unit",
                )
            )

        if self.current_lesson:
            breadcrumb_parts.append((" > ", None))
            breadcrumb_parts.append(
                (
                    f"[bold cyan]Lesson:[/bold cyan] {self.current_lesson['lesson_number']}: {self.current_lesson['title']}",
                    "lesson",
                )
            )

        if self.current_block:
            breadcrumb_parts.append((" > ", None))
            breadcrumb_parts.append(
                (
                    f"[bold cyan]Block:[/bold cyan] {self.current_block['block_number']}: {self.current_block['title']}",
                    "block",
                )
            )

        # Create the breadcrumb panel
        breadcrumb_content = ""
        for text, _ in breadcrumb_parts:
            breadcrumb_content += text

        breadcrumb_panel = Panel(
            breadcrumb_content,
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
            padding=(1, 2),
        )

        self.console.print(breadcrumb_panel)

    def navigate_breadcrumb(self, level):
        """Navigate to specific level in the breadcrumb hierarchy"""
        if level == "home":
            # Reset everything
            self.current_student = None
            self.current_course = None
            self.current_unit = None
            self.current_lesson = None
            self.current_block = None
            self.current_lesson_record = None
        elif level == "student":
            # Reset to student level
            self.current_unit = None
            self.current_lesson = None
            self.current_block = None
            self.current_lesson_record = None
        elif level == "unit":
            # Reset to unit level
            self.current_lesson = None
            self.current_block = None
            self.current_lesson_record = None
        elif level == "lesson":
            # Reset to lesson level
            self.current_block = None

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
            self.console.print("[yellow]No students found.[/yellow]")
            return

        # Create rich table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            title="Student Roster",
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
        )

        table.add_column("ID", style="dim", justify="right")
        table.add_column("Name", style="bright_white")
        table.add_column("Email", style="cyan")
        table.add_column("Course", style="green")

        for s in students:
            table.add_row(str(s["id"]), s["name"], s["email"], s["course_name"])

        self.console.print(table)
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
            self.console.print(
                f"[yellow]No units found for course '{self.current_course['name']}'.[/yellow]"
            )
            return

        # Create rich table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            title=f"Units in {self.current_course['name']}",
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
        )

        table.add_column("ID", style="dim", justify="right")
        table.add_column("Number", style="cyan", justify="center")
        table.add_column("Title", style="bright_white")
        table.add_column("Description", style="green", max_width=60, no_wrap=False)

        for u in units:
            description = u["description"] or "No description available"
            if len(description) > 60:
                description = description[:57] + "..."

            table.add_row(str(u["id"]), str(u["unit_number"]), u["title"], description)

        self.console.print(table)
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
            self.console.print(
                f"[yellow]No lessons found for unit '{self.current_unit['title']}'.[/yellow]"
            )
            return

        # Create rich table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            title=f"Lessons in Unit {self.current_unit['unit_number']}: {self.current_unit['title']}",
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
        )

        table.add_column("ID", style="dim", justify="right")
        table.add_column("Number", style="cyan", justify="center")
        table.add_column("Title", style="bright_white")
        table.add_column("Grammar Focus", style="green", max_width=30, no_wrap=False)
        table.add_column("Vocabulary Focus", style="blue", max_width=30, no_wrap=False)
        table.add_column("Status", justify="center")

        for lesson in lessons:
            grammar = lesson["grammar_focus"] or "None"
            if len(grammar) > 30:
                grammar = grammar[:27] + "..."

            vocab = lesson["vocabulary_focus"] or "None"
            if len(vocab) > 30:
                vocab = vocab[:27] + "..."

            # Define status styles and icons
            status_style = "green bold" if lesson["status"] == "Completed" else "yellow"
            status_icon = "✅" if lesson["status"] == "Completed" else "⏳"

            # Add the status with icon and color
            table.add_row(
                str(lesson["id"]),
                str(lesson["lesson_number"]),
                lesson["title"],
                grammar,
                vocab,
                f"[{status_style}]{status_icon} {lesson['status']}[/{status_style}]",
            )

        self.console.print(table)
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

        # Display lesson info in rich panels
        context = self.current_lesson["context"] or "No context provided."
        context_panel = Panel(
            context,
            title="[bold cyan]📝 CONTEXT[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            expand=True,
            padding=(1, 2),
        )
        self.console.print(context_panel)

        grammar_focus = (
            self.current_lesson["grammar_focus"] or "No grammar focus specified."
        )
        grammar_panel = Panel(
            grammar_focus,
            title="[bold green]📊 GRAMMAR FOCUS[/bold green]",
            border_style="green",
            box=ROUNDED,
            expand=True,
            padding=(1, 2),
        )
        self.console.print(grammar_panel)

        vocab_focus = (
            self.current_lesson["vocabulary_focus"] or "No vocabulary focus specified."
        )
        vocab_panel = Panel(
            vocab_focus,
            title="[bold blue]📚 VOCABULARY FOCUS[/bold blue]",
            border_style="blue",
            box=ROUNDED,
            expand=True,
            padding=(1, 2),
        )
        self.console.print(vocab_panel)

        if grammar_rules:
            self.console.print("\n[bold green]📘 GRAMMAR RULES[/bold green]")
            self.console.print("─" * self.terminal_width)

            for rule in grammar_rules:
                text = Text()
                text.append("\n• ", style="green")
                text.append(rule["rule"], style="bright_white")
                if rule["example"]:
                    text.append("\n  Example: ", style="cyan")
                    text.append(rule["example"], style="yellow")
                self.console.print(text)

        if vocabulary:
            self.console.print("\n[bold blue]📖 VOCABULARY LIST[/bold blue]")
            self.console.print("─" * self.terminal_width)

            vocab_table = Table(
                show_header=True,
                header_style="bold blue",
                box=ROUNDED,
                border_style="blue",
                expand=True,
            )

            vocab_table.add_column("Word/Phrase", style="yellow")
            vocab_table.add_column(
                "Definition", style="bright_white", max_width=40, no_wrap=False
            )
            vocab_table.add_column(
                "Example Usage", style="green", max_width=40, no_wrap=False
            )

            for v in vocabulary:
                vocab_table.add_row(
                    v["word_or_phrase"],
                    v["definition"] or "No definition",
                    v["example_usage"] or "No example",
                )

            self.console.print(vocab_table)

        if resources:
            self.console.print("\n[bold magenta]🔗 RESOURCES[/bold magenta]")
            self.console.print("─" * self.terminal_width)

            for res in resources:
                text = Text()
                text.append("\n• ", style="magenta")
                text.append(f"{res['resource_type']}: ", style="bright_white bold")
                text.append(
                    res["description"] or "No description", style="bright_white"
                )
                text.append("\n  Location: ", style="cyan")
                text.append(res["url_or_path"], style="yellow underline")
                self.console.print(text)

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
            self.console.print(
                f"[yellow]No blocks found for lesson '{self.current_lesson['title']}'.[/yellow]"
            )
            return

        # Create rich table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            title=f"Blocks in Lesson {self.current_lesson['lesson_number']}: {self.current_lesson['title']}",
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
        )

        table.add_column("ID", style="dim", justify="right")
        table.add_column("Number", style="cyan", justify="center")
        table.add_column("Title", style="bright_white")
        table.add_column("Activity Type", style="yellow")
        table.add_column("Status", justify="center")

        for b in blocks:
            # Get activity icon
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

            # Define status styles and icons
            status_style = "green bold" if b["status"] == "Completed" else "yellow"
            status_icon = "✅" if b["status"] == "Completed" else "⏳"

            # Add the status with icon and color
            table.add_row(
                str(b["id"]),
                str(b["block_number"]),
                b["title"],
                f"{activity_icon} {b['activity_type'] or 'Not specified'}",
                f"[{status_style}]{status_icon} {b['status']}[/{status_style}]",
            )

        self.console.print(table)
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
        """Display details about the current block and allow interactive note updates."""
        if not self.current_block:
            self.print_error("No block selected. Please select a block first.")
            return

        while True:  # Loop to keep the user on the block details screen
            self.print_header(
                f"BLOCK {self.current_block['block_number']}: {self.current_block['title']}"
            )

            query = """
            SELECT * FROM block_records
            WHERE lesson_record_id = ? AND block_id = ?
            """
            block_record = self.execute_query(
                query,
                (self.current_lesson_record["id"], self.current_block["id"]),
                "one",
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

            activity_text = Text()
            activity_text.append(
                f"\n{activity_icon} Activity Type: ", style="bold yellow"
            )
            activity_text.append(
                f"{self.current_block['activity_type'] or 'Not specified'}",
                style="yellow",
            )
            self.console.print(activity_text)

            # Display description and content in nice panels
            description = (
                self.current_block["description"] or "No description provided."
            )
            desc_panel = Panel(
                description,
                title="[bold cyan]📋 DESCRIPTION[/bold cyan]",
                border_style="cyan",
                box=ROUNDED,
                expand=True,
                padding=(1, 2),
            )
            self.console.print(desc_panel)

            content = self.current_block["content"] or "No content provided."
            content_panel = Panel(
                content,
                title="[bold green]📄 CONTENT[/bold green]",
                border_style="green",
                box=ROUNDED,
                expand=True,
                padding=(1, 2),
            )
            self.console.print(content_panel)

            if block_record:
                # Display teaching notes in rich panels
                speech_notes = (
                    block_record["student_speech_notes"] or "No notes recorded yet."
                )
                speech_panel = Panel(
                    speech_notes,
                    title="[bold yellow]🗣️ STUDENT SPEECH NOTES[/bold yellow]",
                    border_style="yellow",
                    box=ROUNDED,
                    expand=True,
                    padding=(1, 2),
                )
                self.console.print(speech_panel)

                teacher_notes = (
                    block_record["teacher_notes"] or "No notes recorded yet."
                )
                teacher_panel = Panel(
                    teacher_notes,
                    title="[bold blue]👨‍🏫 TEACHER NOTES[/bold blue]",
                    border_style="blue",
                    box=ROUNDED,
                    expand=True,
                    padding=(1, 2),
                )
                self.console.print(teacher_panel)

                student_q = (
                    block_record["student_questions"] or "No questions recorded yet."
                )
                question_panel = Panel(
                    student_q,
                    title="[bold magenta]❓ STUDENT QUESTIONS[/bold magenta]",
                    border_style="magenta",
                    box=ROUNDED,
                    expand=True,
                    padding=(1, 2),
                )
                self.console.print(question_panel)
            # Interactive input section for updating notes
            self.console.print("\n[bold]Update Notes:[/bold]")
            self.console.print("1. Update Student Speech Notes")
            self.console.print("2. Update Teacher Notes")
            self.console.print("3. Update Student Questions")
            self.console.print("4. Generate Teacher Notes using Gemini")  # New option
            self.console.print("5. Back to Menu")

            note_choice = input("\nEnter your choice (1-5): ")

            if note_choice == "1":
                self.console.print(
                    "\n[bold yellow]📝 Update Student Speech Notes[/bold yellow]"
                )
                self.console.print(
                    "Enter your notes below. You can write multiple lines."
                )
                self.console.print("Type 'END' on a new line to finish.\n")
                new_notes = []
                while True:
                    line = input()
                    if line.strip().upper() == "END":
                        break
                    new_notes.append(line)
                new_notes = "\n".join(new_notes)
                if new_notes.strip():
                    self.update_block_notes(student_speech_notes=new_notes)
                    self.print_success("Student speech notes updated successfully.")
                    input(
                        "\nPress Enter to continue..."
                    )  # Pause for user to read success message
            elif note_choice == "2":
                self.console.print("\n[bold blue]📝 Update Teacher Notes[/bold blue]")
                self.console.print(
                    "Enter your notes below. You can write multiple lines."
                )
                self.console.print("Type 'END' on a new line to finish.\n")
                new_notes = []
                while True:
                    line = input()
                    if line.strip().upper() == "END":
                        break
                    new_notes.append(line)
                new_notes = "\n".join(new_notes)
                if new_notes.strip():
                    self.update_block_notes(teacher_notes=new_notes)
                    self.print_success("Teacher notes updated successfully.")
                    input(
                        "\nPress Enter to continue..."
                    )  # Pause for user to read success message
            elif note_choice == "3":
                self.console.print(
                    "\n[bold magenta]📝 Update Student Questions[/bold magenta]"
                )
                self.console.print(
                    "Enter your questions below. You can write multiple lines."
                )
                self.console.print("Type 'END' on a new line to finish.\n")
                new_questions = []
                while True:
                    line = input()
                    if line.strip().upper() == "END":
                        break
                    new_questions.append(line)
                new_questions = "\n".join(new_questions)
                if new_questions.strip():
                    self.update_block_notes(student_questions=new_questions)
                    self.print_success("Student questions updated successfully.")
                    input(
                        "\nPress Enter to continue..."
                    )  # Pause for user to read success message
            elif note_choice == "4":
                self.generate_teacher_notes_with_gemini()  # New method
            elif note_choice == "5":
                break  # Exit the loop and return to the menu
            else:
                self.print_error("Invalid choice. Please try again.")
                input(
                    "\nPress Enter to continue..."
                )  # Pause for user to read error message

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
        """Display the main menu with rich formatting"""
        self.print_header("MAIN MENU")

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
            (
                "15",
                "🧭 Navigate Breadcrumbs",
                any(
                    [
                        self.current_student,
                        self.current_unit,
                        self.current_lesson,
                        self.current_block,
                    ]
                ),
            ),
            ("16", "🔍 Search Menu", True),  # New search menu option
            ("17", "🤖 Gemini ESL Assistant", True),  # New Gemini option
            ("0", "🚪 Exit", True),
        ]

        # Create a rich table for the menu
        menu_table = Table(
            show_header=False,
            box=ROUNDED,
            border_style="bright_blue",
            expand=True,
            padding=(0, 2),
        )

        menu_table.add_column("Choice", style="bold cyan", justify="right")
        menu_table.add_column("Option", style="bright_white")

        for item in menu_items:
            if item[2]:  # Only display if enabled
                menu_table.add_row(item[0], item[1])

        self.console.print(menu_table)
        self.print_footer()

    def show_search_menu(self):
        """Display the search submenu."""
        while True:
            self.print_header("SEARCH MENU")
            self.console.print("1. Google Search", style="bold cyan")
            self.console.print("2. Google Images", style="bold cyan")
            self.console.print("3. Google News", style="bold cyan")
            self.console.print("4. Search in /assets", style="bold cyan")
            self.console.print("5. Back to Main Menu", style="bold cyan")

            choice = input("\nChoose an option (1-5): ").strip()

            if choice == "1":
                self.google_search("Google Search")
            elif choice == "2":
                self.google_search("Google Images")
            elif choice == "3":
                self.google_search("Google News")
            elif choice == "4":
                self.search_local_assets()
            elif choice == "5":
                break  # Return to the main menu
            else:
                self.print_error("Invalid choice. Try again!")

            # Pause to allow user to read output
            input("\nPress Enter to continue...")

    def use_gemini_assistant(self):
        """Use Gemini AI as a teaching assistant"""
        self.print_header("GEMINI ESL ASSISTANT")

        # Setup Gemini API
        if not self.setup_gemini_api():
            input("\nPress Enter to return to main menu...")
            return

        try:
            # Initialize the model
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Context based on current selection
            context = self.get_current_context()

            self.console.print(
                Panel(
                    "[bold yellow]Gemini ESL Assistant[/]\n\n"
                    "Ask any questions related to English teaching, lesson planning, or get help with "
                    "explanations for your current student and lesson. Type 'exit' to return to main menu.",
                    box=ROUNDED,
                    border_style="yellow",
                    title="Instructions",
                )
            )

            if context:
                self.console.print(
                    Panel(
                        context,
                        box=ROUNDED,
                        border_style="cyan",
                        title="Current Context",
                    )
                )

            # Start chat session
            chat = model.start_chat(history=[])

            while True:
                user_input = prompt(
                    "\n[ESL Assistant] What would you like help with? > "
                )

                if user_input.lower() in ["exit", "quit", "back"]:
                    break

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    task = progress.add_task("[cyan]Generating response...", total=None)

                    if context and not chat.history:  # First message, add context
                        full_prompt = f"{context}\n\nTeacher's question: {user_input}"
                    else:
                        full_prompt = user_input

                    response = chat.send_message(full_prompt)

                # Display the response
                self.console.print(
                    Panel(
                        response.text,
                        box=ROUNDED,
                        border_style="green",
                        title="Gemini's Response",
                    )
                )

        except Exception as e:
            self.print_error(f"Error using Gemini API: {str(e)}")

        input("\nPress Enter to return to main menu...")

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
                elif choice == "15" and any(
                    [
                        self.current_student,
                        self.current_unit,
                        self.current_lesson,
                        self.current_block,
                    ]
                ):
                    self.print_header("BREADCRUMB NAVIGATION")
                elif choice == "16":
                    self.show_search_menu()
                elif choice == "17":  # Add this case for the Gemini option
                    self.use_gemini_assistant()

                    # Create navigation options based on current selection level
                    nav_options = [("0", "Home", "home")]

                    if self.current_student:
                        nav_options.append(
                            ("1", f"Student: {self.current_student['name']}", "student")
                        )

                    if self.current_unit:
                        nav_options.append(
                            (
                                "2",
                                f"Unit {self.current_unit['unit_number']}: {self.current_unit['title']}",
                                "unit",
                            )
                        )

                    if self.current_lesson:
                        nav_options.append(
                            (
                                "3",
                                f"Lesson {self.current_lesson['lesson_number']}: {self.current_lesson['title']}",
                                "lesson",
                            )
                        )

                    # Display options
                    nav_table = Table(
                        show_header=False,
                        box=ROUNDED,
                        border_style="bright_blue",
                        expand=True,
                        padding=(0, 2),
                    )

                    nav_table.add_column("Choice", style="bold cyan", justify="right")
                    nav_table.add_column("Level", style="bright_white")

                    for option in nav_options:
                        nav_table.add_row(option[0], option[1])

                    self.console.print(nav_table)

                    # Get user choice
                    nav_choice = input(
                        "\nNavigate to level (or press Enter to cancel): "
                    )

                    if nav_choice and nav_choice.isdigit():
                        nav_choice = int(nav_choice)
                        if 0 <= nav_choice < len(nav_options):
                            level = nav_options[nav_choice][2]
                            self.navigate_breadcrumb(level)
                            self.print_success(
                                f"Navigated to {nav_options[nav_choice][1]}"
                            )
                else:
                    self.print_error("Invalid choice. Please try again.")

                # Pause to allow user to read output
                input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print("\nExiting ESL Teacher CLI...")
        except sqlite3.Error as e:
            self.print_error(f"Database error: {e}")
        except (ValueError, TypeError) as e:
            self.print_error(f"Input error: {e}")
        except IOError as e:
            self.print_error(f"I/O error: {e}")
        finally:
            self.close_db()
            print("\nGoodbye!")


if __name__ == "__main__":
    cli = ESLTeacherCLI()
    cli.run_cli()
