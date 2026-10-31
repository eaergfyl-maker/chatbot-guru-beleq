# CUQ usability test plan

The lecturer's recommended testing method for Chapter 4 is the Chatbot Usability Questionnaire (Holmes et al., 2019). It has 16 statements answered from 1 (strongly disagree) to 5 (strongly agree). Odd statements are positive and even statements are negative.

**Score** = ((sum of odd items - 8) + (40 - sum of even items)) / 64 x 100, giving a score out of 100.

Check the wording in `eval/cuq.py` against the official usage guide before testing. The guide also offers a calculation tool you can use to cross-check the scores: https://www.ulster.ac.uk/research/topic/computer-science/artificial-intelligence/projects/cuq

## Running a session

1. Decide the number of testers with your lecturer and record it in the report. Testers should not be the project's authors.
2. Start the app with `streamlit run app.py` and press **Start over** in the sidebar for each tester.
3. Ask the tester to do these tasks without help:
   - Tell the bot your name and read the menu.
   - Complete one lesson.
   - Ask two questions of your own about the Gendang Beleq, and include a typing mistake in one.
   - Ask something unrelated, and enter some nonsense.
   - Take the quiz, and ask for a hint at least once.
   - Ask for a recommendation, then look at your progress.
4. Ask the tester to fill in the **Rate this chatbot** form in the sidebar, or run `python -m eval.cuq collect`. Responses are stored in `eval/cuq_responses.csv` under a random ID, with no names.

## Reporting

Run `python -m eval.cuq report` for the mean, standard deviation, range and item means. Report these in Chapter 4 and discuss the lowest-scoring items as future improvements. Do not report a result until real testers have completed it.

## Reference

Holmes, S., Moorhead, A., Bond, R., Zheng, H., Coates, V. and McTear, M. (2019) 'Usability testing of a healthcare chatbot: Can we use conventional methods to assess conversational user interfaces?', *Proceedings of the 31st European Conference on Cognitive Ergonomics*, pp. 207-214. doi:10.1145/3335082.3335094.
