def build_file_list_tree(file_list_tree, sub_dict, parent="", full_path=""):
    """ Recursively builds a hierarchical file list in the Treeview widget. """
    for name, child_obj in sorted(sub_dict.items()):
        if not name:
            continue  # Skip empty names

        new_path = (full_path + "/" + name).strip("/")
        if isinstance(child_obj, dict):
            node_id = file_list_tree.insert(
                parent, "end", text=name, values=(new_path,)
            )  # Insert directory into the tree
            build_file_list_tree(file_list_tree, child_obj, node_id, new_path)  # Recursively process subdirectories
        else:
            file_list_tree.insert(
                parent, "end", text=name, values=(new_path,)
            )  # Insert file into the tree
