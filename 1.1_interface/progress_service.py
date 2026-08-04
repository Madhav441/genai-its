from firebase_admin import firestore

def get_quizzes_completed(student_id):
    db = firestore.client()
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
    db = firestore.client()

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

    print("Quiz percentages:", quiz_percentages)
    print("Average:", sum(quiz_percentages) / len(quiz_percentages))
    return sum(quiz_percentages) / len(quiz_percentages)


def get_improvement_rate(student_id):
    """
    Returns the student's performance improvement between attempts.
    Compares the first attempt score with the latest attempt score
    for each completed question.
    """

    db = firestore.client()

    docs = db.collection("student_performance").stream()

    improvements = []

    for doc in docs:
        if not doc.id.startswith(student_id + "_"):
            continue

        data = doc.to_dict()
        answers = data.get("answers", {})

        for attempts in answers.values():

            if len(attempts) < 2:
                continue

            first_attempt = attempts[0]
            latest_attempt = attempts[-1]

            first_score = first_attempt.get("score", 0)
            latest_score = latest_attempt.get("score", 0)

            improvement = latest_score - first_score

            improvements.append(improvement)

    if not improvements:
        return 0

    average_improvement = sum(improvements) / len(improvements)

    return average_improvement * 100