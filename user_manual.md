# User Manual for GenAI Quiz System

## Overview
The GenAI Quiz System is a robust, multi-user platform designed to facilitate interactive quizzes and learning experiences. It supports advanced features such as LLM integration, PDF and OCR-based question extraction, and persistent state management using Firestore. This manual provides guidance for both students and teachers/tutors on how to use the system effectively.

---

## Table of Contents
1. [Getting Started](#getting-started)
2. [Student Perspective](#student-perspective)
   - [Scenario 1: Taking a Quiz](#scenario-1-taking-a-quiz)
3. [Teacher/Tutor Perspective](#teacher-tutor-perspective)
   - [Scenario 2: Managing Quizzes and Student Performance](#scenario-2-managing-quizzes-and-student-performance)
4. [FAQs](#faqs)
5. [Troubleshooting](#troubleshooting)

---

## Getting Started
1. **Login**: Students and teachers/tutors can log in using the dropdown menu to select their ID. New users can register by selecting the "Add new student" or "Add new teacher" option.
2. **Subject Selection**: After logging in, select the subject you wish to interact with.
3. **Navigation**: Use the sidebar to navigate between quizzes and chat (for teachers/tutors only).

---

## Student Perspective

### Scenario 1: Taking a Quiz
1. **Login**:
   - Select your student ID from the dropdown menu.
   - If you are a new student, click "Add new student" and follow the registration steps.
   - *[Insert Screenshot: Student Login Dropdown]*

2. **Subject Selection**:
   - Choose the subject for which you want to take a quiz.
   - *[Insert Screenshot: Subject Selection Screen]*

3. **Pre-Quiz Survey**:
   - Complete the pre-quiz survey (if shown). This survey is displayed only once per student.
   - *[Insert Screenshot: Pre-Quiz Survey Screen]*

4. **Taking the Quiz**:
   - The quiz will start automatically after the survey.
   - Answer the questions displayed on the screen. You can navigate between questions using the "Next" and "Previous" buttons.
   - *[Insert Screenshot: Quiz Question Screen]*

5. **Post-Quiz Survey**:
   - After completing the quiz, fill out the post-quiz survey (if shown).
   - *[Insert Screenshot: Post-Quiz Survey Screen]*

6. **End of Quiz**:
   - After submitting the quiz and completing the post-quiz survey, you will return to the main page.

---

## Teacher/Tutor Perspective

### Scenario 2: Managing Quizzes and Student Performance
1. **Login**:
   - Select your teacher/tutor ID from the dropdown menu.
   - If you are a new teacher, click "Add new teacher" and follow the registration steps.
   - *[Insert Screenshot: Teacher Login Dropdown]*

2. **Subject and Quiz Management**:
   - Navigate to the "Manage Quizzes" section from the sidebar.
   - Upload new quiz materials (PDFs) or edit existing quizzes.
   - *[Insert Screenshot: Manage Quizzes Screen]*

3. **Monitoring Student Performance**:
   - Access the "Performance Dashboard" to view individual and class-wide performance metrics.
   - Filter results by student, subject, or week.
   - *[Insert Screenshot: Performance Dashboard Screen]*

4. **Providing Feedback**:
   - Use the chat feature to provide personalized feedback to students.
   - *[Insert Screenshot: Chat Feedback Screen]*

---

## FAQs
1. **What if I forget my ID?**
   - Contact your teacher/tutor to retrieve your ID.
2. **Can I retake a quiz?**
   - Yes, but pre- and post-quiz surveys will not be shown again.
3. **How is my data stored?**
   - All data is securely stored in Firestore.

---

## Troubleshooting
1. **Login Issues**:
   - Ensure you select the correct ID from the dropdown.
   - For new registrations, double-check the format of your ID.
2. **Quiz Not Loading**:
   - Check your internet connection.
   - Contact your teacher/tutor if the issue persists.
3. **Performance Dashboard Not Updating**:
   - Refresh the page or log out and log back in.

---

## Notes
- This manual is a living document and will be updated as new features are added.
- For further assistance, contact the system administrator.
