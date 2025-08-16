from constants import NEW, LEARNING, RELEARNING, REVIEW
import datetime
import numpy as np

class Card:
    def __init__(self, question, answer, set_id):
        self.last_review_time = None
        self.wpm = 0
        self.max_wpm = 0
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
        self.max_wpm = max(self.max_wpm, self.wpm)
        self.last_review_time = datetime.datetime.now()
    
    def get_state(self):
        days_since_last_review = (datetime.datetime.now() - self.last_review_time).days if self.last_review_time else 0
        print(type(days_since_last_review))
        return np.array([self.learn_state / 3, self.wpm / self.max_wpm if self.max_wpm > 0 else 0, days_since_last_review / 90])