import subprocess
import tempfile
import os

def run_code(user_code, input_data=""):

    try:

        # create temporary python file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp:

            temp.write(user_code.encode())
            temp_filename = temp.name

        # run the code with timeout
        result = subprocess.run(
            ["python", temp_filename],
            input=input_data.strip() + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8", 
            timeout=2
        )

        output = result.stdout.strip()

        os.remove(temp_filename)

        return output if result.stdout else result.stderr.strip()

    except subprocess.TimeoutExpired:
        return "Time Limit Exceeded"

    except Exception as e:
        return "Error"