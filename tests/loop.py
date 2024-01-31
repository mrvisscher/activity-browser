import subprocess

number = 100
output_file_path = "output.txt"
file = open(output_file_path, 'w')

success = 0
failed = 0

for i in range(1, number + 1):
    file.write(f" test session {i} ".center(79,'#'))
    completed = subprocess.run("pytest tests\\threading_stress_test.py", stdout=subprocess.PIPE, text=True)
    if completed.returncode == 0: success = success + 1
    else: failed = failed + 1
    file.write(completed.stdout)
    print(f"Tests completed: {i}/{number} | Success = {success} | Failed = {failed}")

file.close()