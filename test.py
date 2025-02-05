import json

# Read JSON data from file
with open('test23.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Iterate over the schedule
for day_schedule in data:
    for day, timetable in day_schedule.items():
        print(f"Day: {day}")
        for period, lessons in timetable.items():
            print(f"Period: {period}")
            for lesson_number, lesson_info in lessons.items():
                print(f"Lesson {lesson_number}:")
                print(f"\tName: {lesson_info['name']}")
                print(f"\tTeacher: {lesson_info['teacher']}")
                print(f"\tRoom: {lesson_info['cab']}")
            print()


