from firebase_admin import firestore

db = firestore.client()

def get_quizzes_completed(student_id):
    """
    Returns the number of completed quiz documents
    for the given student.
    """
    # initialise count to 0
    count = 0

    docs = db.collection("student_performance").stream()

    for doc in docs:
        doc_id = doc.id

        if doc_id.startswith(student_id + "_"):
            count += 1

    return count

def get_average_score(student_id):
    """
    Returns the student's average score across all completed quizzes.
    """

    docs = db.collection("student_performance").stream()

    quiz_percentages = []

    for doc in docs:
        if not doc.id.startswith(student_id + "_"):
            continue

        data = doc.to_dict()
        answers = data.get("answers", {})

        if not answers:
            continue

        #calculate the percentage of correct answers for this quiz
        total_questions = 0
        correct_questions = 0

        for question_attempts in answers.values():
            if not question_attempts:
                continue

            latest_attempt = question_attempts[-1]
            total_questions += 1

            if latest_attempt.get("score", 0) == 1:
                correct_questions += 1

        if total_questions > 0:
            percentage = (correct_questions / total_questions) * 100
            quiz_percentages.append(percentage)

    if not quiz_percentages:
        return 0

    return (sum(quiz_percentages) / len(quiz_percentages), 1)