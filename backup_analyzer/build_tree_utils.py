from collections import defaultdict

def build_tree(file_info_list):
    """ Converts the backup file list into a tree structure. """
    tree = defaultdict(dict)
    path_map = {}

    for fileID, domain, rel_path, flags in file_info_list:
        parts = rel_path.strip("/").split("/")
        current_level = tree[domain]
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                current_level = current_level.setdefault(part, {})
            else:
                current_level[part] = {}

    return dict(tree), path_map

def build_backup_tree(tree_widget, file_tree):
    """ Builds the backup file tree structure in the UI. """
    path_dict = {}
    backup_tree_nodes = {}

    # Clear the existing tree
    tree_widget.delete(*tree_widget.get_children())

    # Create root nodes for different file categories
    system_node = tree_widget.insert("", "end", text="System Files")
    user_app_node = tree_widget.insert("", "end", text="User App Files")
    app_group_node = tree_widget.insert("", "end", text="App Group Files")
    app_plugin_node = tree_widget.insert("", "end", text="App Plugin Files")

    def insert_tree(parent, current_dict, current_path=""):
        """ Recursively inserts directories and files into the tree widget. """
        path_dict[current_path] = current_dict
        for name, child_obj in sorted(current_dict.items()):
            if not name:
                continue
            if isinstance(child_obj, dict):
                subdirs = {k: v for k, v in child_obj.items() if k and isinstance(v, dict)}
                if subdirs:
                    new_path = (current_path + "/" + name).strip("/")
                    node_id = tree_widget.insert(parent, "end", text=name, values=(new_path,))
                    backup_tree_nodes[new_path] = node_id
                    insert_tree(node_id, child_obj, new_path)

    # Categorize and insert file domains into the respective nodes
    for domain, sub_dict in sorted(file_tree.items()):
        if "AppDomainGroup" in domain:
            insert_tree(app_group_node, {domain: sub_dict}, domain)
        elif "AppDomainPlugin" in domain:
            insert_tree(app_plugin_node, {domain: sub_dict}, domain)
        elif "HomeDomain" in domain or "AppDomain-" in domain:
            insert_tree(user_app_node, {domain: sub_dict}, domain)
        else:
            insert_tree(system_node, {domain: sub_dict}, domain)

    return path_dict, backup_tree_nodes