import ast
import sys


def extract_structure(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)

    structure = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            structure.append(f"import {' '.join(alias.name for alias in node.names)}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ""  # Handle "from . import X"
            structure.append(
                f"from {module} import {', '.join(alias.name for alias in node.names)}"
            )
        elif isinstance(node, ast.Assign):
            # Capture constants (by convention, variables in UPPER_CASE)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    structure.append(f"{target.id} = ...")
        elif isinstance(node, ast.ClassDef):
            structure.append(f"class {node.name}:")
            for class_body in node.body:
                if isinstance(class_body, ast.FunctionDef):
                    structure.append(
                        f"    def {class_body.name}({', '.join(arg.arg for arg in class_body.args.args)}): ..."
                    )
        elif isinstance(node, ast.FunctionDef):
            structure.append(
                f"def {node.name}({', '.join(arg.arg for arg in node.args.args)}): ..."
            )

    return "\n".join(structure)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <file.py>")
    else:
        print(extract_structure(sys.argv[1]))
