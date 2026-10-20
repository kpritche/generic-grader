# Generic Grader

A collection of generic tests for grading programming assignments.

**This project is still in very early development.  Expect breaking changes.**

## Installation

``` bash
pip install generic-grader
```

## Usage

1. Name the reference solution `reference.py`, and place it in a `tests`
   subdirectory of the directory containing the student's code.

2. Add a configuration file for the assignment in the `tests` subdirectory (e.g.
   `tests/config.py`).  It might look something like this:

   ``` python
   from parameterized import param
   from generic_grader.style import comments # Import the tests you want to use
   from generic_grader.utils.options import Options

   # Create tests by calling each test type's build method.
   # They should all start with the word `test_` to be discovered by unittest.
   # Adding a number after `test_` can be used to control the run order.
   # The argument is a list of `param` objects, each with an `Options` object.
   # See the Options class for more information on the available options.
   test_01_TestCommentLength = comments.build(
      [
         param(
             Options(
                 sub_module="hello_user",
                 hint="Check the volume of comments in your code.",
                 entries=("Tim the Enchanter",),
             ),
         ),
         param(
             Options(
                 sub_module="hello_user",
                 hint="Check the volume of comments in your code.",
                 entries=("King Arthur",),
             ),
         ),
      ]
   )
   ```

3. Run the tests.

   ``` bash
   python -m unittest tests/config.py
   ```

## Programming standards checks

Six checks in `generic_grader.style` grade code quality rather than output.
Each lists every problem it finds by line number.

| Check | Fails when |
|---|---|
| `header` | The header docstring is missing, keeps template placeholder text, has a description under 8 words, or lacks Assignment/Author; or a function other than `main` has no docstring naming its parameters and what it returns |
| `structure` | An import sits inside a function or after code, code runs outside a function, template instruction lines remain, or `main()`/the `__main__` block is missing (when the reference has them) |
| `comment_coverage` | A variable initialized to a number (or read with `input()`) has no comment giving its units, or calculations/output run with no comment nearby |
| `formatting` | More than 3 lines have tab or non-multiple-of-4 indentation, missing spaces around `=`/comparisons or after commas, lines over `max_line_length`, two statements on one line, or no blank line before a top-level `def` |
| `names` | A name overwrites a built-in or an imported module, or is a single letter or filler word (loop variables exempt) |
| `hardcoding` | A number is typed into a calculation or comparison, or a decimal result is typed into output text |

Names and numbers the reference uses are always allowed; `allowed_names` and
`allowed_literals` add to them, and `max_violations` sets how many problems a
check tolerates.  To score a check as a rubric deduction, give it `weight=0`
and a `deduction`: it then scores `-deduction` when it fails and 0 when it
passes, so the assignment's point total does not change.

``` python
from generic_grader.style import header, names
from generic_grader.utils.options import Options

test_90_TestHeader = header.build(Options(sub_module="hello_user", deduction=0.1))
test_91_TestNames = names.build(Options(sub_module="hello_user", deduction=0.1))
```


## Contributing

1. Clone the repo onto your machine.

   - HTTPS

     ``` bash
     git clone https://github.com/Purdue-EBEC/generic-grader.git
     ```

   - SSH

     ``` bash
     git clone git@github.com:Purdue-EBEC/generic-grader.git
     ```

2. Set up a new virtual environment in the cloned repo.

   ``` bash
   cd generic-grader
   python3.12 -m venv .env3.12
   ```

3. Activate the virtual environment.  If you are using VS Code, there may be a
   pop-up to do this automatically when working from this directory.

   - Linux/macOS

      ``` bash
      source .env3.12/bin/activate
      ```

   - Windows

     ``` bash
     .env3.12\Scripts\activate
     ```

4. Install tesseract-ocr

   - on Linux

     ``` bash
     sudo apt install tesseract-ocr
     ```

   - on macOS

     ``` bash
     brew install tesseract
     ```

   - on Windows, download the latest installers from https://github.com/UB-Mannheim/tesseract/wiki

5. Install ghostscript

   - on Linux

     ``` bash
     sudo apt install ghostscript
     ```

   - on macOS

     ``` bash
     brew install ghostscript
     ```

   - on Windows, download the latest installers from https://ghostscript.com/releases/gsdnld.html

6. Install the package.  Note that this installs the package as editable, so
   edits will be automatically reflected in the installed package.

   ``` bash
   pip install -e .[dev]
   ```
   or

   ``` bash
   uv sync --extra dev
   ```

7. Install the pre-commit hooks.

   ``` bash
   pre-commit install
   ```

8. Run the tests.

   ``` bash
   pytest
   ```

9. Make changes ...

10. Deactivate the virtual environment.

   ``` bash
   deactivate
   ```
