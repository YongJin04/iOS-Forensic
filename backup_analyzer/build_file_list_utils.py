def build_file_list_tree(file_list_tree, sub_dict, parent="", full_path="", current_depth=0, max_depth=1):
    """ Recursively builds a hierarchical file list in the Treeview widget. """
    for item in file_list_tree.get_children():
        file_list_tree.delete(item)
    
    if not sub_dict:
        return
    
    for name, child_obj in sorted(sub_dict.items()):
        if not name:
            continue  
        
        if current_depth == 0:
            if isinstance(child_obj, dict):
                node_id = file_list_tree.insert(
                    parent, "end", text=name, values=(name,)
                )
                if max_depth > 1:
                    build_file_list_tree(file_list_tree, child_obj, node_id, full_path + "/" + name, current_depth + 1, max_depth)
            else:
                file_list_tree.insert(
                    parent, "end", text=name, values=(name,)
                )
        
        elif current_depth == 1 and isinstance(child_obj, dict):
            file_list_tree.insert(
                parent, "end", text=name, values=(name,)
            )
        elif current_depth == 1 and not isinstance(child_obj, dict):
            file_list_tree.insert(
                parent, "end", text=name, values=(name,)
            )