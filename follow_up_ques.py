# -*- coding: utf-8 -*-
"""Follow Up ques.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1rYGJVkOkj6CVEljccwJUiqDyLgTSMT9o
"""

import os
import anthropic
import re
from difflib import SequenceMatcher

# Set up Claude client
client = anthropic.Anthropic(api_key="")

# Stores previous Q&A for each session
conversation_history = {}

# Quality thresholds
QUALITY_THRESHOLD = 0.6  # Minimum similarity score for relevance
MIN_QUALITY_SCORE = 6  # Minimum score for an AI-generated question


def feedback_info(question_text, answer_text, session_id):
    """ Generates structured feedback on the candidate's answer. """
    if not question_text or not answer_text:
        raise ValueError("Both question_text and answer_text are required.")

    prompt = f"""
    Return JSON data containing eval_summary, what_went_well, what_can_be_improved, and next_steps by evaluating
    the following product management interview answer based on the GRAIL framework:

    Question: {question_text}
    Answer: {answer_text}

    Output:
    - eval_summary: Summary of response quality.
    - what_went_well: 4-5 strengths in the response.
    - what_can_be_improved: 3-4 areas for improvement.
    - next_steps: Concise suggestions for refining the answer.
    """

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            system="You extract interview feedback info into structured JSON.",
            messages=[{"role": "user", "content": prompt}],
        )

        json_body = response.content[0].text.strip()

        # Ensure session exists before storing history
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        conversation_history[session_id].append({"question": question_text, "answer": answer_text})

        return json_body
    except Exception as e:
        print(f"Error generating feedback: {e}")
        return None


def quality_control_check(question_text, answer_text, ai_response):
    """ Ensures AI-generated follow-up questions meet quality standards. """
    try:
        # 🔹 Step 1: Contextual Relevance Check
        relevance_prompt = f"""
        Analyze the following follow-up question for contextual relevance.

        Candidate's Response: {answer_text}
        AI-Generated Follow-Up Question: {ai_response}

        On a scale from **1 to 10**, how well does this follow-up question logically relate to the candidate's response?
        (A score of 1 means it is completely unrelated, 10 means it is perfectly relevant.)

        Score (just a number, no explanation):
        """

        validation_response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=100,
            system="You verify AI responses for relevance.",
            messages=[{"role": "user", "content": relevance_prompt}],
        )

        score_text = validation_response.content[0].text.strip()
        score_match = re.search(r"\d+", score_text)
        relevance_score = int(score_match.group()) if score_match else 5  # Default to 5 if extraction fails

        if relevance_score < 6:
            #print("Warning: AI-generated question may not be contextually relevant!")
            return {"valid": False, "reason": f"Low relevance score ({relevance_score}/10)."}

        # 🔹 Step 2: Scoring System for Response Quality
        scoring_prompt = f"""
        Evaluate the quality of the AI-generated follow-up question based on clarity, relevance, and depth.
        Give a score from 1 to 10, with **ONLY the number** as the response.

        Question: {question_text}
        Candidate Response: {answer_text}
        AI-Generated Follow-Up Question: {ai_response}

        Score (just a number, no explanation):
        """

        scoring_response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=100,
            system="You score AI responses for clarity and quality.",
            messages=[{"role": "user", "content": scoring_prompt}],
        )

        score_text = scoring_response.content[0].text.strip()
        score_match = re.search(r"\d+", score_text)
        score = int(score_match.group()) if score_match else 5  # Default to 5 if extraction fails

        if score < MIN_QUALITY_SCORE:
            print(f"⚠ Warning: AI-generated question scored low (score: {score}/10).")
            return {"valid": False, "reason": f"Low-quality response (score: {score}/10)."}

        return {"valid": True, "reason": "AI-generated follow-up question is high quality."}

    except Exception as e:
        print(f"Error in quality control check: {e}")
        return {"valid": False, "reason": "Quality control system failed."}


def generate_follow_up_question(session_id):
    """ Generates dynamic follow-up questions with quality control. """
    if session_id not in conversation_history or len(conversation_history[session_id]) == 0:
        raise ValueError("No conversation history found for session.")

    history = conversation_history[session_id]

    new_question = None
    is_valid = False
    attempts = 0
    while not is_valid and attempts < 5:  # Allow 5 attempts
        attempts += 1

        prompt = f"""
        You are a professional interviewer conducting a product management interview.
        Your goal is to generate a **natural and engaging** follow-up question while ensuring a dynamic, non-linear conversation.

        ### **Conversation Context**
        - **Original Interview Question:** "{history[0]['question']}"
        - **Last Question Asked:** "{history[-1]['question']}"
        - **Candidate’s Last Response:** "{history[-1]['answer']}"
        - **Previous Related Answers:** { [entry['answer'] for entry in history] }

        Now, based on the conversation flow, generate a well-structured and engaging follow-up question.
        """

        try:
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=150,
                system="You generate high-quality follow-up questions.",
                messages=[{"role": "user", "content": prompt}],
            )
            new_question = response.content[0].text.strip()

        except Exception as e:
            print(f"Error generating follow-up question: {e}")
            return "Sorry, an error occurred."

        check = quality_control_check(history[-1]["question"], history[-1]["answer"], new_question)
        is_valid = check["valid"]

    return new_question


# 🔹 Example Interview Session
session_id = "session_123"

if __name__ == "__main__":
    question = "Tell me about your recent product"
    answer = "I am working on an AI interviewer"

    # Step 1: Generate feedback
    feedback = feedback_info(question, answer, session_id)
    print("\n Feedback Summary:")
    print(feedback)

    # Step 2: Generate dynamic follow-up question
    for i in range(10):
        follow_up_question = generate_follow_up_question(session_id)
        print(f"\n Follow-Up Question {i + 1}: {follow_up_question}")

        # Take user input as the candidate's answer
        candidate_response = input("\n🗣️ Enter candidate's answer: ")

        # Store the new response in history
        conversation_history[session_id].append({"question": follow_up_question, "answer": candidate_response})

