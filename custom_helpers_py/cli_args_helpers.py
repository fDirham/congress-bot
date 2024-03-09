import sys


def get_args(max_num_args=5):
    to_return = []

    num_args = len(sys.argv) - 1
    for i in range(max_num_args):
        if i < num_args:
            to_return.append(sys.argv[i + 1])
        else:
            to_return.append(None)

    return to_return
