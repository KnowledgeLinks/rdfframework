""" MODULE for git as in github utilities """

def mod_git_ignore(directory, ignore_item, action):
    """ checks if an item is in the specified gitignore file and adds it if it
    is not in the file
    """
    if not os.path.isdir(directory):
        return
    ignore_filepath = os.path.join(directory,".gitignore")
    if not os.path.exists(ignore_filepath):
        items = []
    else:
        with open(ignore_filepath) as ig_file:
            items = ig_file.readlines()
    # strip and clean the lines
    clean_items  = [line.strip("\n").strip() for line in items]
    clean_items = make_list(clean_items)
    if action == "add":
        if ignore_item not in clean_items:
            with open(ignore_filepath, "w") as ig_file:
                clean_items.append(ignore_item)
                ig_file.write("\n".join(clean_items) + "\n")
    elif action == "remove":
        with open(ignore_filepath, "w") as ig_file:
            for i, value in enumerate(clean_items):
                if value != ignore_item.lower():
                    ig_file.write(items[i])