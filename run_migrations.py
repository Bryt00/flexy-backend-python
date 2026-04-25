import subprocess
import sys

def run_command(command, inputs=None):
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True
    )
    
    if inputs:
        input_str = "\n".join(inputs) + "\n"
        stdout, stderr = process.communicate(input=input_str)
    else:
        stdout, stderr = process.communicate()
    
    return process.returncode, stdout, stderr

print("Running makemigrations rides...")
r, out, err = run_command("python manage.py makemigrations rides")
print(out, err)

print("Running makemigrations marketing...")
r, out, err = run_command("python manage.py makemigrations marketing", ["y"])
print(out, err)

print("Running migrate...")
r, out, err = run_command("python manage.py migrate")
print(out, err)
