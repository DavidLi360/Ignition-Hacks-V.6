from constants import NEW, LEARNING, RELEARNING, REVIEW

class Card:
    def __init__(self, question, answer, set_id):
        self.last_review_time = None
        self.wpm = 0
        self.learn_state = NEW

        self.question = question
        self.answer = answer
        self.set_id = set_id

    def review(self, wpm, is_correct):
        if is_correct:
            if self.learn_state == NEW:
                self.learn_state = LEARNING
            elif self.learn_state in [LEARNING, RELEARNING]:
                self.learn_state = REVIEW

        elif self.learn_state == REVIEW:
            self.learn_state = RELEARNING

        elif self.learn_state == NEW:
            self.learn_state = LEARNING

        self.wpm = wpm if is_correct else 0