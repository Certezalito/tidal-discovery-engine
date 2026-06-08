import re
with open('tests/test_gemini_service.py', 'r') as f:
    data = f.read()

data = data.replace('gemini_service._cap_recommendations(recommendations, 0), None', 'gemini_service._cap_recommendations(recommendations, 0), []')
data = data.replace('gemini_service._cap_recommendations(recommendations, -3), None', 'gemini_service._cap_recommendations(recommendations, -3), []')

with open('tests/test_gemini_service.py', 'w') as f:
    f.write(data)
