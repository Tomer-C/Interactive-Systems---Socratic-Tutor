import ast


def analyze_code_structure(code_str):
    """
    Parses Python code and returns a set of structural tags.
    Returns: set(['Loops', 'Recursion', 'Syntax', ...])
    """
    features = set()
    try:
        tree = ast.parse(code_str)

        # Walk the tree to find constructs
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                features.add("Loops")
            elif isinstance(node, ast.If):
                features.add("Conditionals")
            elif isinstance(node, ast.FunctionDef):
                features.add("Functions")
            elif isinstance(node, ast.ClassDef):
                features.add("Classes")

        # Simple heuristic for recursion
        if "Functions" in features:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and \
                                isinstance(child.func, ast.Name) and \
                                child.func.id == func_name:
                            features.add("Recursion")

    except SyntaxError:
        features.add("Syntax")
    except Exception:
        pass
    return features