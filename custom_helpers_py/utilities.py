def get_percentage_string(curr_idx, start_idx, last_idx):
    normalized_idx = curr_idx - start_idx
    normalized_last_idx = last_idx - start_idx
    done_fraction = normalized_idx / normalized_last_idx
    done_pct: float = done_fraction * 100
    done_pct_string = "{:10.2f}%".format(done_pct)
    return done_pct_string
