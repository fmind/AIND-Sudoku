from collections import Counter
from functools import reduce

import sys
sys.setrecursionlimit(10000)

DIGITS = '123456789'
COLS = '123456789'
ROWS = 'ABCDEFGHI'

partition = lambda n, coll: [coll[i:i + n] for i in range(0, len(coll), n)]
cross = lambda a, b: [s + t for s in a for t in b]


# simply add diagonal units to extend constraint propagation to diagonals in the grid
DUNITS = [[r + c for i, r in enumerate(ROWS, 1) for j, c in enumerate(COLS, 1) if i + j == 10],
          [r + c for i, r in enumerate(ROWS, 1) for j, c in enumerate(COLS, 1) if i == j]]
SUNITS = [cross(rs, cs) for rs in partition(3, ROWS) for cs in partition(3, COLS)]
RUNITS = [cross(r, COLS) for r in ROWS]
CUNITS = [cross(ROWS, c) for c in COLS]
BOXES = cross(ROWS, COLS)

UNITLIST = DUNITS + SUNITS + RUNITS + CUNITS
UNITS = dict((box, [u for u in UNITLIST if box in u]) for box in BOXES)
PEERS = dict((box, set(sum(UNITS[box], [])) - set([box])) for box in BOXES)

assignments = []


def assign_value(values, box, value):
    """
    Please use this function to update your values dictionary!
    Assigns a value to a given box. If it updates the board record it.
    """
    values[box] = value

    if len(value) == 1:
        assignments.append(values.copy())

    return values


def naked_twins(values):
    """Eliminate values using the naked twins strategy.
    Args:
        values(dict): a dictionary of the form {'box_name': '123456789', ...}

    Returns:
        the values dictionary with the naked twins eliminated from peers.
    """
    # apply the naked twins constraint on each unit of the grid
    # use frozenset to ensure the search is order insensitive
    # e.g. '12' and '21' are considered twins in this version
    for unit in UNITLIST:
        # find pairs in the unit: box where the current solution has two digits
        pairs = {box: frozenset(values[box]) for box in unit if len(values[box]) == 2}
        # find twins in pairs: pairs that appear exactly two times in the dict
        twins = [pair for pair, n in Counter(pairs.values()).items() if n == 2]

        # no twins found: go to next unit
        if len(twins) == 0:
            continue

        # remove digits from every box in the unit ...
        for box in unit:
            digits = values[box]

            # ... except when the solution has one digit
            if len(digits) == 1:
                continue

            # ... except when the solution is a twin
            if frozenset(values[box]) in twins:
                continue

            # use reduce to remove digits that appear in the (union) of twins
            # another possibility would be to compose a regexp and use string substitution
            digits = reduce(lambda s, d: s.replace(d, ''), frozenset.union(*twins), digits)
            assign_value(values, box, digits)

    return values


def grid_values(grid):
    """
    Convert grid into a dict of {square: char} with '123456789' for empties.
    Args:
        grid(string) - A grid in string form.
    Returns:
        A grid in dictionary form
            Keys: The boxes, e.g., 'A1'
            Values: The value in each box, e.g., '8'. If the box has no value, then the value will be '123456789'.
    """
    values = list()

    for c in grid:
        if c == '.':
            values.append(DIGITS)
        else:
            values.append(c)

    assert(len(values) == 81)
    assert(all(v in DIGITS or v is DIGITS for v in values))

    return dict(zip(BOXES, values))


def display(values):
    """
    Display the values as a 2-D grid.
    Args:
        values(dict): The sudoku in dictionary form
    """
    width = 1 + max(len(values[s]) for s in BOXES)
    line = '+'.join(['-' * (width * 3)] * 3)

    print()

    for r in ROWS:
        print(''.join(values[r + c].center(width) + ('|' if c in '36' else '') for c in COLS))

        if r in 'CF':
            print(line)

    print


def eliminate(values):
    """Eliminate values from peers of each box with a single value.

    Go through all the boxes, and whenever there is a box with a single value,
    eliminate this value from the set of values of all its peers.

    Args:
        values: Sudoku in dictionary form.
    Returns:
        Resulting Sudoku in dictionary form after eliminating values.
    """
    solved = {cell: digits for cell, digits in values.items() if len(digits) == 1}

    for cell, digit in solved.items():
        for peer in PEERS[cell]:
            assign_value(values, peer, values[peer].replace(digit, ''))

    return values


def only_choice(values):
    """Finalize all values that are the only choice for a unit.

    Go through all the units, and whenever there is a unit with a value
    that only fits in one box, assign the value to this box.

    Input: Sudoku in dictionary form.
    Output: Resulting Sudoku in dictionary form after filling in only choices.
    """
    for unit in UNITLIST:
        for digit in DIGITS:
            only = [box for box in unit if digit in values[box]]

            if len(only) == 1:
                assign_value(values, only[0], digit)

    return values


def reduce_puzzle(values):
    """
    Iterate eliminate() and only_choice(). If at some point, there is a box with no available values, return False.
    If the sudoku is solved, return the sudoku.
    If after an iteration of both functions, the sudoku remains the same, return the sudoku.
    Input: A sudoku in dictionary form.
    Output: The resulting sudoku in dictionary form.
    """
    stalled = False

    while not stalled:
        # Check how many boxes have a determined value
        solved_values_before = len([box for box in values.keys() if len(values[box]) == 1])

        # Use the Eliminate Strategy
        values = eliminate(values)

        # Use the Only Choice Strategy
        values = only_choice(values)

        # Use Naked Twins Strategy
        values = naked_twins(values)

        # Check how many boxes have a determined value, to compare
        solved_values_after = len([box for box in values.keys() if len(values[box]) == 1])

        # If no new values were added, stop the loop.
        stalled = solved_values_before == solved_values_after

        # Sanity check, return False if there is a box with zero available values:
        if len([box for box in values.keys() if len(values[box]) == 0]):
            return False

    return values


def search(values):
    "Using depth-first search and propagation, create a search tree and solve the sudoku."
    values = reduce_puzzle(values)

    if values is False:
        return False

    free = [[len(values[box]), box] for box in BOXES if len(values[box]) > 1]

    if len(free) == 0:
        return values

    # Choose one of the unfilled squares with the fewest possibilities
    n, box = min(free)

    # Now use recurrence to solve each one of the resulting sudokus
    for value in values[box]:
        hypothesis = values.copy()
        assign_value(hypothesis, box, value)
        result = search(hypothesis)

        if result:
            return result


def solve(grid):
    """
    Find the solution to a Sudoku grid.
    Args:
        grid(string): a string representing a sudoku grid.
            Example: '2.............62....1....7...6..8...3...9...7...6..4...4....8....52.............3'
    Returns:
        The dictionary representation of the final sudoku grid. False if no solution exists.
    """
    values = grid_values(grid)

    return search(values)


if __name__ == '__main__':
    diag_sudoku_grid = '2.............62....1....7...6..8...3...9...7...6..4...4....8....52.............3'
    display(solve(diag_sudoku_grid))

    try:
        from visualize import visualize_assignments
        visualize_assignments(assignments)

    except SystemExit:
        pass
    except:
        print('We could not visualize your board due to a pygame issue. Not a problem! It is not a requirement.')

# easy_grid = '..3.2.6..' + '9..3.5..1' + '..18.64..' + '..81.29..' + '7.......8' \
#             + '..67.82..' + '..26.95..' + '8..2.3..9' + '..5.1.3..'

# hard_grid = '4.....8.5' + '.3.......' + '...7.....' + '.2.....6.' + '....8.4..' \
#             + '....1....' + '...6.3.7.' + '5..2.....' + '1.4......'

# diag_grid = '2........' + '.....62..' + '..1....7.' + '..6..8...' + '3...9...7' \
#             + '...6..4..' + '.4....8..' + '..52.....' + '........3'

# solution = solve(diag_grid)
# display(solution)
