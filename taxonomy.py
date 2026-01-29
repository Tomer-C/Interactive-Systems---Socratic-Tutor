ERROR_TAXONOMY = {
    "Root": ["Logic_Errors", "Syntax_Errors", "Runtime_Errors"],

    "Logic_Errors": ["Loops", "Recursion", "Conditionals", "Data_Structures"],
    "Syntax_Errors": ["Indentation", "Typos", "Missing_Symbols"],
    "Runtime_Errors": ["ZeroDivision", "IndexError", "TypeError"],

    "Loops": ["Infinite_Loop", "Off_By_One", "For_Loop_Range"],
    "Recursion": ["Missing_Base_Case", "Stack_Overflow", "Incorrect_Recursive_Call"],
    "Conditionals": ["Incorrect_Comparison", "Else_If_Order"],
    "Data_Structures": ["KeyError", "List_Mutation"]
}

PARENT_MAP = {}
for parent, children in ERROR_TAXONOMY.items():
    for child in children:
        PARENT_MAP[child] = parent


def get_common_ancestor(error_list):
    """
    Finds the nearest common ancestor for a list of errors.
    Useful when the system is unsure between two specific bugs.
    """
    if not error_list: return "Root"

    parents = set()
    for err in error_list:
        parents.add(PARENT_MAP.get(err, "Root"))

    if len(parents) == 1:
        return list(parents)[0]

    return "Root"