import os
import sqlite3
import time
from datetime import datetime
import random
import textwrap
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress
from rich.box import ROUNDED


class ESLMobileCompanion:
    """Mobile companion app for ESL students to practice vocabulary and quick exercises"""

    def __init__(self, db_path="esl copy.db"):
        """Initialize the mobile companion app with database connection"""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.current_student = None
        self.current_course = None
        self.terminal_width = min(
            os.get_terminal_size().columns, 60
        )  # Cap width for mobile

        # Set up rich console with constrained width for mobile
        self.console = Console(width=self.terminal_width)

        # Study session variables
        self.vocab_to_review = []
        self.grammar_to_review = []
        self.daily_streak = 0
        self.points = 0
        self.last_study_date = None

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
            return None

    def clear_screen(self):
        """Clear the terminal screen based on OS"""
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self, title):
        """Print a formatted header optimized for mobile"""
        self.clear_screen()

        header_text = Text()
        header_text.append("ESL MOBILE\n", style="bold cyan")
        header_text.append(title, style="bold white")

        header_panel = Panel(
            header_text,
            box=ROUNDED,
            border_style="bright_blue",
            padding=(1, 1),
            width=self.terminal_width,
        )

        self.console.print(header_panel)

    def print_error(self, message):
        """Print error message with formatting"""
        error_panel = Panel(
            f"{message}",
            title="ERROR",
            title_align="left",
            border_style="red",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(error_panel)

    def print_success(self, message):
        """Print success message with formatting"""
        success_panel = Panel(
            f"{message}",
            title="SUCCESS",
            title_align="left",
            border_style="green",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(success_panel)

    def wrap_text(self, text, width=None):
        """Wrap text to fit mobile screen"""
        if width is None:
            width = self.terminal_width - 4
        return textwrap.fill(text, width=width)

    def display_splash_screen(self):
        """Display a splash screen with compact ASCII art for mobile"""
        self.clear_screen()
        splash = """
        ███████╗███████╗██╗     
        ██╔════╝██╔════╝██║     
        █████╗  ███████╗██║     
        ██╔══╝  ╚════██║██║     
        ███████╗███████║███████╗
        ╚══════╝╚══════╝╚══════╝
         ███╗   ███╗ ██████╗ ██████╗ ██╗██╗     ███████╗
         ████╗ ████║██╔═══██╗██╔══██╗██║██║     ██╔════╝
         ██╔████╔██║██║   ██║██████╔╝██║██║     █████╗  
         ██║╚██╔╝██║██║   ██║██╔══██╗██║██║     ██╔══╝  
         ██║ ╚═╝ ██║╚██████╔╝██████╔╝██║███████╗███████╗
         ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚══════╝╚══════╝
        """

        splash_panel = Panel(
            Text(splash, style="bright_cyan"),
            box=ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            width=self.terminal_width,
        )

        self.console.print(splash_panel)
        self.console.print(
            "Vocabulary & Practice Companion", style="bold cyan", justify="center"
        )
        self.console.print("Version 1.0.2", style="cyan", justify="center")

        # Compact loading bar
        with Progress() as progress:
            task = progress.add_task("Starting up...", total=100)
            for i in range(101):
                progress.update(task, completed=i)
                time.sleep(0.01)

    def search_student_by_name(self, name):
        """Search for a student by name"""
        query = "SELECT * FROM enrolled_students WHERE name LIKE ?"
        students = self.execute_query(query, (f"%{name}%",), "all")

        if not students:
            self.print_error("No students found with that name.")
            return None

        # Display the list of students
        self.print_header("SEARCH RESULTS")
        student_table = Table(
            title="[bold]Matching Students[/bold]", box=ROUNDED, border_style="blue"
        )
        student_table.add_column("ID", style="cyan")
        student_table.add_column("Name", style="green")
        student_table.add_column("Email", style="white")

        for student in students:
            student_table.add_row(str(student["id"]), student["name"], student["email"])

        self.console.print(student_table)

        # Allow the user to select a student
        student_id = input("\nEnter the ID of the student you want to select: ")

        # Find the selected student
        selected_student = next(
            (s for s in students if str(s["id"]) == student_id), None
        )

        if not selected_student:
            self.print_error("Invalid student ID.")
            return None

        return selected_student

    def authenticate_student(self):
        """Authenticate a student to use the app"""
        self.print_header("STUDENT LOGIN")

        # Ask the user how they want to log in
        self.console.print("How would you like to log in?\n")
        self.console.print("1. By Student ID")
        self.console.print("2. By Email")
        self.console.print("3. By Name")

        choice = input("\nEnter your choice: ")

        if choice == "1":
            # Log in by Student ID
            student_id = input("Enter Student ID: ")
            query = "SELECT * FROM enrolled_students WHERE id = ?"
            student = self.execute_query(query, (student_id,), "one")
        elif choice == "2":
            # Log in by Email
            email = input("Enter Email: ")
            query = "SELECT * FROM enrolled_students WHERE email = ?"
            student = self.execute_query(query, (email,), "one")
        elif choice == "3":
            # Log in by Name
            name = input("Enter Name: ")
            student = self.search_student_by_name(name)
        else:
            self.print_error("Invalid choice. Please try again.")
            return False

        if not student:
            self.print_error("Student not found. Please try again.")
            return False

        self.current_student = dict(student)

        # Get the course information
        query = "SELECT * FROM courses WHERE id = ?"
        course = self.execute_query(query, (self.current_student["course_id"],), "one")

        if course:
            self.current_course = dict(course)

        # Load student progress
        self.load_student_progress()

        self.print_success(f"Welcome, {self.current_student['name']}!")
        return True

    def load_student_progress(self):
        """Load student's progress, streak, and points from the database"""
        if not self.current_student:
            print("No current student. Cannot load progress.")
            return

        # Check if we have an entry in the mobile_app_progress table
        query = """
        SELECT * FROM mobile_app_progress 
        WHERE student_id = ?
        """
        progress = self.execute_query(query, (self.current_student["id"],), "one")

        if not progress:
            print("No progress record found. Creating a new entry.")
            # Create a new entry if none exists
            query = """
            INSERT INTO mobile_app_progress (student_id, points, streak, last_study_date)
            VALUES (?, 0, 0, ?)
            """
            today = datetime.now().strftime("%Y-%m-%d")
            self.execute_query(query, (self.current_student["id"], today), "commit")
            self.daily_streak = 0
            self.points = 0
            self.last_study_date = today
        else:
            print(f"Progress record found: {progress}")
            self.daily_streak = progress["streak"]
            self.points = progress["points"]
            self.last_study_date = progress["last_study_date"]

            # Update streak if needed
            today = datetime.now().strftime("%Y-%m-%d")
            print(f"Today: {today}")
            print(f"Last Study Date: {self.last_study_date}")

            if self.last_study_date:
                last_date = datetime.strptime(self.last_study_date, "%Y-%m-%d")
                today_date = datetime.strptime(today, "%Y-%m-%d")
                days_diff = (today_date - last_date).days
                print(f"Days Difference: {days_diff}")

                # Debug print statement to verify streak calculation
                print(
                    f"Last Study Date: {self.last_study_date}, Today: {today}, Days Diff: {days_diff}, Streak: {self.daily_streak}"
                )

                if days_diff == 1:
                    # Studied yesterday, increment streak
                    print("Studied yesterday. Incrementing streak.")
                    self.daily_streak += 1
                elif days_diff > 1:
                    # Streak broken
                    print("Streak broken. Resetting streak to 1.")
                    self.daily_streak = 1
            else:
                # No last_study_date, assume this is the first study session
                print("No last study date. Starting new streak.")
                self.daily_streak = 1

            # Update the last_study_date to today
            self.last_study_date = today
            self.update_progress()

    def update_progress(self):
        """Update student progress in the database"""
        if not self.current_student:
            print("No current student. Cannot update progress.")
            return

        today = time.strftime("%Y-%m-%d")
        print(f"Updating progress for student {self.current_student['id']}:")
        print(
            f"Points: {self.points}, Streak: {self.daily_streak}, Last Study Date: {today}"
        )

        query = """
        UPDATE mobile_app_progress
        SET points = ?, streak = ?, last_study_date = ?
        WHERE student_id = ?
        """
        self.execute_query(
            query,
            (self.points, self.daily_streak, today, self.current_student["id"]),
            "commit",
        )
        print("Progress updated in database.")

    def display_student_dashboard(self):
        """Show student dashboard with progress and quick access features"""
        while True:
            self.print_header("YOUR DASHBOARD")

            # Display student info and stats
            student_info = Text()
            student_info.append(f"{self.current_student['name']}\n", style="bold green")
            student_info.append("Course: ", style="cyan")
            student_info.append(f"{self.current_course['name']}\n", style="white")
            student_info.append("🔥 Streak: ", style="yellow")
            student_info.append(f"{self.daily_streak} days\n", style="white")
            student_info.append("✨ Points: ", style="bright_magenta")
            student_info.append(f"{self.points}\n", style="white")

            profile_panel = Panel(
                student_info,
                title="[bold]PROFILE[/bold]",
                border_style="green",
                box=ROUNDED,
                padding=(1, 1),
                width=self.terminal_width,
            )
            self.console.print(profile_panel)

            # Get student progress and display it
            completed_lessons = self.get_student_progress()
            if completed_lessons:
                self.console.print("\n[bold]Recently Completed Lessons:[/bold]")
                for lesson in completed_lessons[
                    :3
                ]:  # Show the last 3 completed lessons
                    self.console.print(
                        f"📚 {lesson['title']} (Unit {lesson['unit_number']}, Lesson {lesson['lesson_number']})"
                    )

            # Show quick actions menu
            self.console.print("\n[bold]Quick Actions:[/bold]")
            self.console.print("1. 📝 Vocabulary Flashcards")
            self.console.print("2. 🔤 Grammar Practice")
            self.console.print("3. 🎯 Daily Challenge")
            self.console.print("4. 📊 Progress Report")
            self.console.print("5. 📚 Recent Lessons")
            self.console.print("0. 🚪 Logout")

            choice = input("\nEnter your choice: ")

            if choice == "0":
                break
            elif choice == "1":
                self.vocabulary_flashcards()
            elif choice == "2":
                self.grammar_practice()
            elif choice == "3":
                self.daily_challenge()
            elif choice == "4":
                self.show_progress_report()
            elif choice == "5":
                self.show_recent_lessons()
            else:
                self.print_error("Invalid choice. Please try again.")
                input("\nPress Enter to continue...")

    def get_student_progress(self):
        """Get student progress from lesson_records"""
        if not self.current_student:
            return []

        query = """
        SELECT lr.*, l.title, l.lesson_number, u.unit_number
        FROM lesson_records lr
        JOIN lessons l ON lr.lesson_id = l.id
        JOIN units u ON l.unit_id = u.id
        WHERE lr.student_id = ? AND lr.completion_date IS NOT NULL
        ORDER BY lr.completion_date DESC
        """
        return self.execute_query(query, (self.current_student["id"],))

    def load_vocabulary_to_review(self):
        """Load vocabulary from completed lessons for review"""
        if not self.current_student:
            return []

        query = """
        SELECT v.* 
        FROM vocabulary v
        JOIN lessons l ON v.lesson_id = l.id
        JOIN lesson_records lr ON l.id = lr.lesson_id
        WHERE lr.student_id = ?
        ORDER BY RANDOM()
        LIMIT 20
        """
        vocabulary = self.execute_query(query, (self.current_student["id"],))
        return vocabulary if vocabulary else []

    def load_grammar_to_review(self):
        """Load grammar rules from completed lessons for review"""
        if not self.current_student:
            return []

        query = """
        SELECT gr.* 
        FROM grammar_rules gr
        JOIN lessons l ON gr.lesson_id = l.id
        JOIN lesson_records lr ON l.id = lr.lesson_id
        WHERE lr.student_id = ?
        ORDER BY RANDOM()
        LIMIT 10
        """
        grammar = self.execute_query(query, (self.current_student["id"],))
        return grammar if grammar else []

    def vocabulary_flashcards(self):
        """Interactive vocabulary flashcard practice"""
        self.print_header("VOCABULARY FLASHCARDS")

        # Load vocabulary if not already loaded
        if not self.vocab_to_review:
            self.vocab_to_review = self.load_vocabulary_to_review()

        if not self.vocab_to_review:
            self.print_error("No vocabulary words found. Complete some lessons first.")
            input("\nPress Enter to continue...")
            return

        correct_count = 0
        total = min(10, len(self.vocab_to_review))  # Limit to 10 cards per session
        practiced_words = []

        for i in range(total):
            word = self.vocab_to_review[i]
            practiced_words.append(word)

            # Display the word
            word_panel = Panel(
                word["word_or_phrase"],
                title="[bold yellow]Word/Phrase[/bold yellow]",
                border_style="yellow",
                box=ROUNDED,
                padding=(1, 1),
                width=self.terminal_width,
            )
            self.console.print(word_panel)

            # Ask if they know it
            self.console.print("\nDo you know the meaning?\n")
            self.console.print("1. Show definition")
            self.console.print("2. I know it")

            choice = input("\nChoice: ")

            if choice == "1":
                # Show definition
                def_panel = Panel(
                    self.wrap_text(word["definition"]),
                    title="[bold green]Definition[/bold green]",
                    border_style="green",
                    box=ROUNDED,
                    padding=(1, 1),
                    width=self.terminal_width,
                )
                self.console.print(def_panel)

                # Initialize example_panel with a default value
                example_panel = None

                # Show example if available
                if word["example_usage"]:
                    example_panel = Panel(
                        self.wrap_text(word["example_usage"]),
                        title="[bold blue]Example Usage[/bold blue]",
                        border_style="blue",
                        box=ROUNDED,
                        padding=(1, 1),
                        width=self.terminal_width,
                    )

                # Only print example_panel if it was defined
                if example_panel:
                    self.console.print(example_panel)

                # Ask if they got it right
                self.console.print("\nDid you know this?\n")
                self.console.print("1. Yes")
                self.console.print("2. No")

                choice = input("\nChoice: ")

                if choice == "1":
                    correct_count += 1
                    self.points += 10  # Award points for correct recall
                else:
                    self.points += 5  # Award fewer points for learning
            elif choice == "2":
                correct_count += 1
                self.points += 15  # Award more points for knowing it without help
            else:
                self.print_error("Invalid choice. No points awarded.")

            # Pause before next card
            input("\nPress Enter to continue...")
            self.clear_screen()

        # Update progress after session
        self.update_progress()

        # Show session results
        self.print_header("FLASHCARD RESULTS")
        results_panel = Panel(
            f"🎯 Correct: {correct_count}/{total}\n"
            f"✨ Points Earned: {self.points}\n"
            f"🔥 Streak: {self.daily_streak} days",
            title="[bold]Session Summary[/bold]",
            border_style="green",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(results_panel)

        # Remove practiced words from review list
        self.vocab_to_review = [
            word for word in self.vocab_to_review if word not in practiced_words
        ]

        input("\nPress Enter to return to the dashboard...")

    def grammar_practice(self):
        """Interactive grammar rule practice"""
        self.print_header("GRAMMAR PRACTICE")

        # Load grammar rules if not already loaded
        if not self.grammar_to_review:
            self.grammar_to_review = self.load_grammar_to_review()

        if not self.grammar_to_review:
            self.print_error("No grammar rules found. Complete some lessons first.")
            input("\nPress Enter to continue...")
            return

        correct_count = 0
        total = min(5, len(self.grammar_to_review))  # Limit to 5 rules per session
        practiced_rules = []

        for i in range(total):
            rule = self.grammar_to_review[i]
            practiced_rules.append(rule)

            # Display the rule
            rule_panel = Panel(
                rule["rule"],
                title="[bold yellow]Grammar Rule[/bold yellow]",
                border_style="yellow",
                box=ROUNDED,
                padding=(1, 1),
                width=self.terminal_width,
            )
            self.console.print(rule_panel)

            # Show example if available
            if rule["example"]:
                example_panel = Panel(
                    self.wrap_text(rule["example"]),
                    title="[bold blue]Example[/bold blue]",
                    border_style="blue",
                    box=ROUNDED,
                    padding=(1, 1),
                    width=self.terminal_width,
                )
                self.console.print(example_panel)

            # Ask if they understand the rule
            self.console.print("\nDo you understand this rule?\n")
            self.console.print("1. Yes")
            self.console.print("2. No")

            choice = input("\nChoice: ")

            if choice == "1":
                correct_count += 1
                self.points += 10  # Award points for understanding
            else:
                self.points += 5  # Award fewer points for learning

            # Pause before next rule
            input("\nPress Enter to continue...")
            self.clear_screen()

        # Update progress after session
        self.update_progress()

        # Show session results
        self.print_header("GRAMMAR PRACTICE RESULTS")
        results_panel = Panel(
            f"🎯 Correct: {correct_count}/{total}\n"
            f"✨ Points Earned: {self.points}\n"
            f"🔥 Streak: {self.daily_streak} days",
            title="[bold]Session Summary[/bold]",
            border_style="green",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(results_panel)

        # Remove practiced rules from review list
        self.grammar_to_review = [
            rule for rule in self.grammar_to_review if rule not in practiced_rules
        ]

        input("\nPress Enter to return to the dashboard...")

    def daily_challenge(self):
        """Provide a daily challenge for the student"""
        self.print_header("DAILY CHALLENGE")

        # Check if the student has already completed today's challenge
        today = time.strftime("%Y-%m-%d")
        query = """
        SELECT * FROM daily_challenges
        WHERE student_id = ? AND date = ?
        """
        challenge = self.execute_query(
            query, (self.current_student["id"], today), "one"
        )

        if challenge:
            self.print_error("You've already completed today's challenge.")
            input("\nPress Enter to continue...")
            return

        # Select a random vocabulary word or grammar rule
        if random.choice([True, False]):
            # Vocabulary challenge
            word = random.choice(self.load_vocabulary_to_review())
            challenge_type = "vocabulary"
            challenge_text = f"Use the word '{word['word_or_phrase']}' in a sentence."
        else:
            # Grammar challenge
            rule = random.choice(self.load_grammar_to_review())
            challenge_type = "grammar"
            challenge_text = (
                f"Create a sentence using the following grammar rule:\n{rule['rule']}"
            )

        # Display the challenge
        challenge_panel = Panel(
            self.wrap_text(challenge_text),
            title="[bold yellow]Your Challenge[/bold yellow]",
            border_style="yellow",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(challenge_panel)

        # Get student's response
        response = input("\nEnter your response: ")

        # Save the challenge
        query = """
        INSERT INTO daily_challenges (student_id, date, challenge_type, challenge_text, student_response)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(
            query,
            (
                self.current_student["id"],
                today,
                challenge_type,
                challenge_text,
                response,
            ),
            "commit",
        )

        # Award points
        self.points += 20
        self.update_progress()

        self.print_success("Challenge completed! Points awarded.")
        input("\nPress Enter to continue...")

    def show_progress_report(self):
        """Display a detailed progress report for the student"""
        self.print_header("PROGRESS REPORT")

        # Get completed lessons
        completed_lessons = self.get_student_progress()

        # Create a table to display progress
        progress_table = Table(
            title="[bold]Completed Lessons[/bold]", box=ROUNDED, border_style="blue"
        )
        progress_table.add_column("Unit", style="cyan")
        progress_table.add_column("Lesson", style="green")
        progress_table.add_column("Title", style="white")
        progress_table.add_column("Completed On", style="magenta")

        for lesson in completed_lessons:
            progress_table.add_row(
                f"Unit {lesson['unit_number']}",
                f"Lesson {lesson['lesson_number']}",
                lesson["title"],
                lesson["completion_date"],
            )

        self.console.print(progress_table)

        # Show vocabulary and grammar progress
        vocab_count = len(self.load_vocabulary_to_review())
        grammar_count = len(self.load_grammar_to_review())

        stats_panel = Panel(
            f"📚 Vocabulary Words Reviewed: {vocab_count}\n"
            f"🔤 Grammar Rules Reviewed: {grammar_count}\n"
            f"✨ Total Points: {self.points}\n"
            f"🔥 Current Streak: {self.daily_streak} days",
            title="[bold]Your Stats[/bold]",
            border_style="green",
            box=ROUNDED,
            padding=(1, 1),
            width=self.terminal_width,
        )
        self.console.print(stats_panel)

        input("\nPress Enter to continue...")

    def show_recent_lessons(self):
        """Display recently completed lessons"""
        self.print_header("RECENT LESSONS")

        # Get completed lessons
        completed_lessons = self.get_student_progress()

        if not completed_lessons:
            self.print_error("No lessons completed yet.")
            input("\nPress Enter to continue...")
            return

        # Display the last 5 lessons
        recent_lessons = completed_lessons[:5]

        for lesson in recent_lessons:
            lesson_panel = Panel(
                f"Unit {lesson['unit_number']}, Lesson {lesson['lesson_number']}\n"
                f"Title: {lesson['title']}\n"
                f"Completed on: {lesson['completion_date']}",
                title="[bold]Lesson[/bold]",
                border_style="blue",
                box=ROUNDED,
                padding=(1, 1),
                width=self.terminal_width,
            )
            self.console.print(lesson_panel)

        input("\nPress Enter to continue...")

    def run(self):
        """Main application loop"""
        self.display_splash_screen()

        if not self.connect_db():
            return

        while True:
            if not self.authenticate_student():
                # Ask if the user wants to exit after a failed login attempt
                self.console.print(
                    "\nWould you like to exit the program? (y/n): ", style="bold red"
                )
                exit_choice = input().strip().lower()
                if exit_choice == "y":
                    self.print_header("EXITING PROGRAM")
                    self.console.print(
                        "Thank you for using ESL Mobile Companion!",
                        style="bold cyan",
                        justify="center",
                    )
                    self.close_db()  # Close the database connection
                    return  # Exit the program
                else:
                    continue  # Continue to the next iteration of the loop

            self.display_student_dashboard()
            self.current_student = None
            self.current_course = None
            self.vocab_to_review = []
            self.grammar_to_review = []

            self.print_header("LOGGED OUT")
            self.console.print(
                "Thank you for using ESL Mobile Companion!",
                style="bold cyan",
                justify="center",
            )

            # Ask if the user wants to exit after logging out
            self.console.print(
                "\nWould you like to exit the program? (y/n): ", style="bold red"
            )
            exit_choice = input().strip().lower()
            if exit_choice == "y":
                self.close_db()  # Close the database connection
                return  # Exit the program
            else:
                continue  # Continue to the next iteration of the loop


if __name__ == "__main__":
    app = ESLMobileCompanion()
    app.run()
